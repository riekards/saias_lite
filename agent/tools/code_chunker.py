import ast
import json
import os
import inspect
from typing import List, Dict, Tuple, Set, Optional
from pathlib import Path
from dataclasses import dataclass
from agent.tools.llm import safe_code_llm, score_code_patch
from agent.tools.dependency_graph import DependencyGraph

@dataclass
class CodeChunk:
	"""Represents a logical code chunk with context"""
	chunk_type: str  # 'function', 'class', 'imports', 'global'
	name: str
	content: str
	start_line: int
	end_line: int
	dependencies: Set[str]  # Names this chunk depends on
	provides: Set[str]  # Names this chunk defines
	imports_needed: Set[str]  # Import statements needed

@dataclass 
class ChunkContext:
	"""Context information for safe refactoring"""
	all_imports: List[str]
	global_variables: Set[str]
	all_functions: Set[str]
	all_classes: Set[str]
	cross_references: Dict[str, Set[str]]  # what each name references

class CodeChunker:
	def __init__(self):
		self.token_limit = 6000  # Conservative limit for 8k context
		
	def chunk_file(self, file_path: str) -> List[CodeChunk]:
		"""Break a Python file into context-aware chunks"""
		with open(file_path, 'r', encoding='utf-8') as f:
			source_code = f.read()
			
		try:
			tree = ast.parse(source_code)
		except SyntaxError as e:
			print(f"[ERROR] Cannot parse {file_path}: {e}")
			return []
			
		lines = source_code.splitlines()
		context = self._build_context(tree, lines)
		chunks = self._extract_chunks(tree, lines, context)
		
		return chunks
	
		# Add global dependency context
		graph = DependencyGraph()
		graph.build()
		rel_path = os.path.relpath(file_path, ROOT_PATH)
		dependents = graph.get_dependents(rel_path)
		if dependents:
			context_warning = f"# WARNING: This file is imported by: {', '.join(dependents)}\n"
			source_code = context_warning + source_code
			lines = source_code.splitlines()

	def _build_context(self, tree: ast.AST, lines: List[str]) -> ChunkContext:
		"""Analyze the entire file to understand dependencies"""
		imports = []
		global_vars = set()
		functions = set()
		classes = set()
		cross_refs = {}
		
		# Collect all top-level definitions
		for node in ast.walk(tree):
			if isinstance(node, (ast.Import, ast.ImportFrom)):
				imports.append(ast.get_source_segment('\n'.join(lines), node) or "")
			elif isinstance(node, ast.FunctionDef):
				functions.add(node.name)
			elif isinstance(node, ast.ClassDef):
				classes.add(node.name)
			elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
				global_vars.add(node.targets[0].id)
		
		# Build cross-reference map
		for node in ast.walk(tree):
			if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
				refs = set()
				for child in ast.walk(node):
					if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
						refs.add(child.id)
				cross_refs[node.name] = refs
				
		return ChunkContext(imports, global_vars, functions, classes, cross_refs)
	
	def _extract_chunks(self, tree: ast.AST, lines: List[str], context: ChunkContext) -> List[CodeChunk]:
		"""Extract logical chunks with proper context"""
		chunks = []
		body_nodes = tree.body
		
		# Create imports chunk if needed
		if context.all_imports:
			imports_content = '\n'.join(context.all_imports)
			chunks.append(CodeChunk(
				chunk_type='imports',
				name='imports',
				content=imports_content,
				start_line=1,
				end_line=len(context.all_imports),
				dependencies=set(),
				provides=set(),
				imports_needed=set()
			))
		
		# Extract classes and functions
		body_nodes = tree.body
		for i, node in enumerate(body_nodes):
			if isinstance(node, ast.FunctionDef):
				next_line = body_nodes[i+1].lineno if i + 1 < len(body_nodes) else len(lines)
				chunk = self._create_function_chunk(node, lines, context, next_line)
				if chunk:
					chunks.append(chunk)
			elif isinstance(node, ast.ClassDef):
				next_line = body_nodes[i+1].lineno if i + 1 < len(body_nodes) else len(lines)
				chunk = self._create_class_chunk(node, lines, context, next_line)
				if chunk:
					chunks.append(chunk)
		
		return chunks
	
	def _create_function_chunk(self, node: ast.FunctionDef, lines: List[str], context: ChunkContext, end_line_hint: int) -> Optional[CodeChunk]:
		"""Create a function chunk with context"""
		start_line = node.lineno - 1
		end_line = getattr(node, 'end_lineno', None) or end_line_hint
		content = '\n'.join(lines[start_line:end_line])
		
		# Analyze dependencies
		dependencies = set()
		for child in ast.walk(node):
			if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
				name = child.id
				if (name in context.all_functions or 
					name in context.all_classes or 
					name in context.global_variables):
					dependencies.add(name)
		
		# Determine needed imports
		imports_needed = self._get_imports_for_dependencies(dependencies, context)
		
		return CodeChunk(
			chunk_type='function',
			name=node.name,
			content=content,
			start_line=start_line + 1,
			end_line=end_line,
			dependencies=dependencies,
			provides={node.name},
			imports_needed=imports_needed
		)
	
	def _create_class_chunk(self, node: ast.ClassDef, lines: List[str], context: ChunkContext, end_line_hint: int) -> Optional[CodeChunk]:
		"""Create a class chunk with context"""
		start_line = node.lineno - 1
		end_line = getattr(node, 'end_lineno', None) or end_line_hint
		content = '\n'.join(lines[start_line:end_line])


		if not end_line:
			# Fallback: try to detect end by walking forward until we hit a top-level line with same indentation
			current_indent = len(lines[start_line]) - len(lines[start_line].lstrip())
			end_line = start_line + 1
			for i in range(start_line + 1, len(lines)):
				line = lines[i]
				# Skip blank lines
				if not line.strip():
					continue
				line_indent = len(line) - len(line.lstrip())
				if line_indent <= current_indent:
					break
				end_line = i + 1  # Include this line

		content = '\n'.join(lines[start_line:end_line])

		# Analyze dependencies
		dependencies = set()
		provides = {node.name}

		for child in ast.walk(node):
			if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
				name = child.id
				if (
					name in context.all_functions or
					name in context.all_classes or
					name in context.global_variables
				):
					dependencies.add(name)
			elif isinstance(child, ast.FunctionDef):
				provides.add(f"{node.name}.{child.name}")

		imports_needed = self._get_imports_for_dependencies(dependencies, context)

		return CodeChunk(
			chunk_type='class',
			name=node.name,
			content=content,
			start_line=start_line + 1,
			end_line=end_line,
			dependencies=dependencies,
			provides=provides,
			imports_needed=imports_needed
		)

	
	def _get_imports_for_dependencies(self, dependencies: Set[str], context: ChunkContext) -> Set[str]:
		"""Determine which imports are needed for the dependencies"""
		needed_imports = set()
		
		# Simple heuristic: include imports that might be related to dependencies
		for imp in context.all_imports:
			for dep in dependencies:
				if dep in imp or any(part.startswith(dep) for part in imp.split()):
					needed_imports.add(imp)
		
		return needed_imports
	
	def create_contextual_prompt(self, chunk: CodeChunk, context: ChunkContext) -> str:
		"""Create a prompt with necessary context for the LLM"""
		prompt_parts = []
		
    # ✅ Always show top-level imports
		if context.all_imports:
			prompt_parts.append("# IMPORTANT: The following imports are already in the file:")
			prompt_parts.extend([f"# {imp}" for imp in context.all_imports])
			prompt_parts.append("")

    # Add dependency context
		if chunk.dependencies:
			prompt_parts.append("# Context - Referenced functions/classes:")
			for dep in chunk.dependencies:
				if dep in context.cross_references:
					prompt_parts.append(f"# {dep} is used in this file")
			prompt_parts.append("")

    # Add the actual chunk
		prompt_parts.append("# Code to refactor:")
		prompt_parts.append(chunk.content)
		return '\n'.join(prompt_parts)
	
	def refactor_chunk(self, chunk: CodeChunk, context: ChunkContext) -> Optional[str]:
		"""Refactor a single chunk with context awareness"""
		contextual_prompt = self.create_contextual_prompt(chunk, context)
		
		# Check token count (rough estimate: 4 chars per token)
		if len(contextual_prompt) > self.token_limit * 4:
			print(f"[WARN] Chunk {chunk.name} too large ({len(contextual_prompt)} chars), skipping")
			return None
		
		print(f"[DEBUG] Refactoring {chunk.chunk_type} '{chunk.name}' with context")
		refactored = safe_code_llm(contextual_prompt)
		
		if refactored and self._validate_chunk_integrity(chunk, refactored, context):
			return refactored
		
		print(f"[WARN] Refactored chunk {chunk.name} failed validation")
		return None
	
	def _validate_chunk_integrity(self, original_chunk: CodeChunk, refactored: str, context: ChunkContext) -> bool:
		try:
			ast.parse(refactored)
		except SyntaxError:
			return False

		# 🔒 Block new top-level imports not in original file
		original_imports = {imp.split()[-1].split('.')[0] for imp in context.all_imports}
		try:
			refactored_tree = ast.parse(refactored)
			for node in ast.walk(refactored_tree):
				if isinstance(node, (ast.Import, ast.ImportFrom)):
					module = getattr(node, 'module', '')
					if module and module.split('.')[0] not in original_imports:
						print(f"[BLOCK] Unauthorized import: {module}")
						return False
		except Exception:
			return False

		# ✅ Preserve public interface
		new_provides = set()
		for node in ast.walk(refactored_tree):
			if isinstance(node, ast.FunctionDef):
				new_provides.add(node.name)
			elif isinstance(node, ast.ClassDef):
				new_provides.add(node.name)

		critical = original_chunk.provides.intersection(context.all_functions | context.all_classes)
		if not critical.issubset(new_provides):
			print(f"[BLOCK] Missing: {critical - new_provides}")
			return False

		return True
	
	def reassemble_chunks(self, chunks: List[Tuple[CodeChunk, str]], original_lines: List[str]) -> str:
		"""Reassemble refactored chunks back into a complete file"""
		result_lines = original_lines.copy()
		
		# Sort chunks by line number (reverse order for proper replacement)
		sorted_chunks = sorted(chunks, key=lambda x: x[0].start_line, reverse=True)
		
		for original_chunk, refactored_code in sorted_chunks:
			start_idx = original_chunk.start_line - 1
			end_idx = original_chunk.end_line
			
			# Replace the original chunk with refactored version
			refactored_lines = refactored_code.split('\n')
			result_lines[start_idx:end_idx] = refactored_lines
		
		return '\n'.join(result_lines)

def chunk_and_refactor_file(file_path: str) -> Optional[str]:
	"""Main function to chunk and refactor a file"""
	chunker = CodeChunker()
	chunks = chunker.chunk_file(file_path)
	
	if not chunks:
		print(f"[ERROR] No chunks extracted from {file_path}")
		return None, []
	
	# Build context once
	with open(file_path, 'r', encoding='utf-8') as f:
		source_code = f.read()
		
	try:
		tree = ast.parse(source_code)
		lines = source_code.splitlines()
		context = chunker._build_context(tree, lines)
	except Exception as e:
		print(f"[ERROR] Failed to build context: {e}")
		return None, []
	
	# Refactor each chunk
	refactored_chunks = []
	total_score = 0
	chunk_metadata = []
	
	for chunk in chunks:
		if chunk.chunk_type == 'imports':
			continue  # Don't refactor imports
			
		refactored = chunker.refactor_chunk(chunk, context)
		if refactored:
			score = score_code_patch(refactored, chunk.content)
			chunk_metadata.append({
                "chunk_id": f"{chunk.chunk_type}:{chunk.name}:{chunk.start_line}",
                "chunk_type": chunk.chunk_type,
                "name": chunk.name,
                "score": score,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "original": chunk.content,
                "refactored": refactored
            })
			total_score += score
			refactored_chunks.append((chunk, refactored))
			print(f"[SUCCESS] {chunk.name} refactored (score: {score}/10)")
		else:
			print(f"[SKIP] Failed to refactor {chunk.name}")
	
	if not refactored_chunks:
		print("[INFO] No chunks were successfully refactored")
		return None, []
	
	# Reassemble the file
	result = chunker.reassemble_chunks(refactored_chunks, lines)
	avg_score = total_score / len(refactored_chunks) if refactored_chunks else 0
	
	print(f"[SUMMARY] Refactored {len(refactored_chunks)} chunks, average score: {avg_score:.1f}/10")
	return result, chunk_metadata

if __name__ == "__main__":
	# Test with a sample file
	test_file = input("Enter file path to chunk and refactor: ").strip()
	if os.path.exists(test_file):
		result = chunk_and_refactor_file(test_file)
		if result:
			print("\n" + "="*50)
			print("REFACTORED CODE:")
			print("="*50)
			print(result)
	else:
		print(f"File {test_file} not found.")