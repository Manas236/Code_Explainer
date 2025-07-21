# 🧠 Code Explainer with Gemini AI

This Python project uses Google's Gemini model to **detect the programming language**, **split code into functions**, **generate natural language explanations**, and **add inline comments** to source code files.

It can be used to quickly understand unfamiliar codebases, especially useful for students, reviewers, or engineers exploring new repositories.

## 📁 Project Structure

The core of the project is a class (presumably named `CodeExplainer` or similar) with the following functionality:

---

## 🧩 Class Methods Overview

### `__init__(self)`
Initializes the class, sets up API keys, model configurations, or other required setup tasks.

### `query_gemini(self, prompt: str, max_tokens: int = 1000) -> str`
Queries Gemini with a custom prompt and retrieves the generated response. Used internally by other methods.

---

## 🔍 Language Detection

### `detect_language(self, code: str) -> str`
Detects the programming language of the input code using a custom method.

### `detect_language_with_gemini(self, code: str) -> str`
Uses Gemini to identify the programming language from the input code snippet.

### `detect_language_fallback(self, code: str) -> str`
Fallback method for language detection using heuristic or rule-based approaches.

---

## 🛠️ Code Processing

### `split_code_into_functions(self, code: str) -> List[Tuple[str, str]]`
Splits the input code into a list of `(function_name, function_code)` tuples, useful for modular analysis.

---

## 🧠 Code Explanation

### `explain_code_with_gemini(self, code: str, language: str, is_full_code: bool = True) -> str`
Explains a block of code or full script using Gemini. Accepts code, its language, and whether it's full code or a snippet.

### `explain_code_block_simple(self, code: str, language: str = "python") -> str`
Provides a simple, readable explanation of a small block of code.

---

## 📝 Inline Comments

### `generate_inline_comments(self, code: str, language: str) -> str`
Adds inline comments to the code using Gemini.

### `_generate_comments_rule_based(self, code: str, language: str) -> str`
A rule-based method to add inline comments without using an LLM.

### `_generate_line_comment(self, line: str, language: str) -> str`
Generates a comment for a single line of code using heuristic logic.

---

## 📦 Utility

### `explain_code(self, code: str, add_comments: bool = True) -> Dict[str, str]`
High-level method that takes code, optionally adds inline comments, and returns structured explanation in dictionary format.

---

## 🚀 Entry Point

### `main()`
Main function that can be used to load a file, run the explainer, and print/save results.

---

## 🔧 Requirements

- Python 3.8+
- `google.generativeai` or similar (Gemini SDK)
- (Optional) `Pygments` for syntax highlighting
- `.env` for API key management (optional but recommended)

---

## 📌 Example Usage

```python
from explainer import CodeExplainer

code = '''
def add(a, b):
    return a + b
'''

explainer = CodeExplainer()
language = explainer.detect_language(code)
explanation = explainer.explain_code_with_gemini(code, language)
print(explanation)
