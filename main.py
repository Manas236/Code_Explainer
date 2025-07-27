import streamlit as st
import requests
import json
import re
import os
from typing import Dict, List, Tuple, Optional
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Configure Streamlit page
st.set_page_config(
    page_title="ML Code Explainer with Gemini",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Prompt user for the Gemini API key at the very beginning
api_key = st.text_input("Enter your Gemini API Key:", type="password")

# If no API key is entered yet, show warning and stop
if not api_key:
    st.warning("Please enter your Gemini API key to proceed.")
    st.stop()



class GeminiCodeExplainer:
    def __init__(self):
        """Initialize the Code Explainer with Gemini API"""
        

        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
        
        if not self.api_key:
            st.error("GEMINI_API_KEY not found in environment variables!")
            st.stop()
    
    def query_gemini(self, prompt: str, max_tokens: int = 1000) -> str:
        """Query Gemini API with a prompt"""
        try:
            headers = {
                "Content-Type": "application/json",
            }
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": max_tokens,
                    "stopSequences": []
                }
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    return "No response generated"
            else:
                return f"Error: HTTP {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error querying Gemini: {str(e)}"
    
    def detect_language(self, code: str) -> str:
        """Enhanced language detection"""
        # Python patterns
        python_patterns = [
            r'\bdef\b', r'\bimport\b', r'\bfrom\b.*\bimport\b', r'\bprint\s*\(',
            r'\bif\s+.*:', r'\bfor\s+.*:', r'\bwhile\s+.*:', r'\btry\s*:',
            r'\bclass\s+\w+.*:', r'\bwith\s+.*:', r'\bexcept\s*.*:'
        ]
        
        # JavaScript patterns
        js_patterns = [
            r'\bfunction\b', r'\bconst\b', r'\blet\b', r'\bvar\b', r'=>',
            r'\bconsole\.log\b', r'\bdocument\b', r'\bwindow\b', r'\breturn\b',
            r'{\s*$', r'}\s*$'
        ]
        
        # Java patterns
        java_patterns = [
            r'\bpublic\s+class\b', r'\bpublic\s+static\b', r'\bprivate\b',
            r'\bprotected\b', r'\bSystem\.out\.println\b', r'\bvoid\b',
            r'\bString\b', r'\bint\b', r'\bboolean\b'
        ]
        
        # C++ patterns
        cpp_patterns = [
            r'\b#include\b', r'\bstd::', r'\bint\s+main\b', r'\bcout\b',
            r'\bcin\b', r'\bnamespace\b', r'\busing\s+namespace\b'
        ]
        
        # Count matches for each language
        scores = {
            'python': sum(1 for pattern in python_patterns if re.search(pattern, code)),
            'javascript': sum(1 for pattern in js_patterns if re.search(pattern, code)),
            'java': sum(1 for pattern in java_patterns if re.search(pattern, code)),
            'cpp': sum(1 for pattern in cpp_patterns if re.search(pattern, code))
        }
        
        # Return language with highest score
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'python'
    
    def split_code_into_functions(self, code: str) -> List[Tuple[str, str]]:
        """Split code into minimal logical blocks to reduce API calls"""
        # For free tier, limit to max 2 blocks to avoid overloading
        functions = []
        lines = code.split('\n')
        
        # Look for major function/class definitions only
        major_blocks = []
        current_block = []
        
        for line in lines:
            stripped = line.strip()
            
            # Detect major function/class definitions only
            if (re.match(r'^\s*def\s+(\w+)', line) or 
                re.match(r'^\s*class\s+(\w+)', line) or
                re.match(r'^\s*function\s+(\w+)', line)):
                
                # Save previous block if exists and is substantial
                if current_block and len('\n'.join(current_block).strip()) > 50:
                    major_blocks.append('\n'.join(current_block))
                
                # Start new block
                current_block = [line]
            else:
                current_block.append(line)
        
        # Add the last block
        if current_block:
            major_blocks.append('\n'.join(current_block))
        
        # Limit to maximum 2 blocks for free tier
        if len(major_blocks) > 2:
            # Combine smaller blocks
            first_half = major_blocks[:len(major_blocks)//2]
            second_half = major_blocks[len(major_blocks)//2:]
            
            functions.append(("first_section", '\n'.join(first_half)))
            functions.append(("second_section", '\n'.join(second_half)))
        else:
            for i, block in enumerate(major_blocks):
                if len(block.strip()) > 10:  # Only include substantial blocks
                    functions.append((f"section_{i+1}", block))
        
        return functions if functions else [("main_code", code)]
    
    def explain_code_with_gemini(self, code: str, language: str, is_full_code: bool = True) -> str:
        """Generate concise explanation using Gemini API"""
        
        if is_full_code:
            # For full code, use comprehensive prompt
            prompt = f"""Explain this {language} code concisely:

{code}

Provide: 1) What it does, 2) Key components, 3) How it works. Keep it under 200 words."""
        else:
            # For code blocks, use simpler prompt
            prompt = f"""Briefly explain this {language} code section:

{code}

What does this part do? Keep it short and clear."""

        explanation = self.query_gemini(prompt, max_tokens=800)
        
        # If explanation has errors, use fallback
        if "Error" in explanation or len(explanation) < 20:
            return self.explain_code_block_simple(code, language)
        
        return explanation
    
    def explain_code_block_simple(self, code: str, language: str = "python") -> str:
        """Generate explanation using rule-based approach as fallback"""
        explanation = f"**{language.title()} Code Analysis:**\n\n"
        
        lines = code.split('\n')
        key_features = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue
            
            # Function definitions
            if re.match(r'^\s*def\s+(\w+)', line):
                func_name = re.match(r'^\s*def\s+(\w+)', line).group(1)
                key_features.append(f"**Function Definition**: Defines `{func_name}()` function")
            
            # Class definitions
            elif re.match(r'^\s*class\s+(\w+)', line):
                class_name = re.match(r'^\s*class\s+(\w+)', line).group(1)
                key_features.append(f"**Class Definition**: Defines `{class_name}` class")
            
            # Variable assignments
            elif re.match(r'^\s*(\w+)\s*=', line):
                var_name = re.match(r'^\s*(\w+)\s*=', line).group(1)
                key_features.append(f"**Variable Assignment**: Creates/assigns variable `{var_name}`")
            
            # Control structures
            elif re.match(r'^\s*if\s+', line):
                key_features.append("**Conditional Logic**: Contains if statement for decision making")
            elif re.match(r'^\s*for\s+', line):
                key_features.append("**Loop Structure**: Uses for loop for iteration")
            elif re.match(r'^\s*while\s+', line):
                key_features.append("**Loop Structure**: Uses while loop for repetition")
            elif re.match(r'^\s*try\s*:', line):
                key_features.append("**Error Handling**: Implements try-except for error management")
            
            # Return statements
            elif re.match(r'^\s*return\s+', line):
                key_features.append("**Return Statement**: Returns value from function")
            
            # Import statements
            elif re.match(r'^\s*import\s+', line):
                key_features.append("**Module Import**: Imports external libraries/modules")
            
            # Print/output statements
            elif re.match(r'^\s*print\s*\(', line):
                key_features.append("**Output**: Displays information to console")
        
        # Format the features
        if key_features:
            explanation += "\n".join(f"• {feature}" for feature in key_features)
        else:
            explanation += "• Contains basic programming logic and statements"
        
        return explanation
    
    def generate_inline_comments(self, code: str, language: str) -> str:
        """Generate inline comments using simple prompt"""
        
        prompt = f"""Add brief comments to this {language} code:

{code}

Add # comments for important lines only. Keep comments short."""

        commented_code = self.query_gemini(prompt, max_tokens=1000)
        
        # If Gemini fails, use rule-based approach
        if "Error" in commented_code or len(commented_code) < len(code):
            return self._generate_comments_rule_based(code, language)
        
        return commented_code
    
    def detect_language_with_gemini(self, code: str) -> str:
        """Use Gemini API for accurate language detection"""
        prompt = f"""Identify the programming language of this code. Respond with ONLY the language name (e.g., "python", "javascript", "java", "csharp", "cpp", "typescript", "go", "rust", "kotlin", "swift", "php", "ruby", "scala", "dart", "r", "matlab", "sql", "html", "css", "bash", "powershell", "yaml", "json", "xml").

Code:
{code[:1000]}  # Limit to first 1000 characters for efficiency

Language:"""
        
        try:
            response = self.query_gemini(prompt, max_tokens=50)
            
            # Clean up the response
            language = response.lower().strip()
            
            # Handle common variations
            language_mapping = {
                "c#": "csharp",
                "c sharp": "csharp",
                "c++": "cpp",
                "c plus plus": "cpp",
                "js": "javascript",
                "ts": "typescript",
                "py": "python",
                "rb": "ruby",
                "sh": "bash",
                "shell": "bash",
                "powershell": "powershell",
                "ps1": "powershell",
                "yml": "yaml",
                "objective-c": "objectivec",
                "objc": "objectivec"
            }
            
            # Check for exact matches first
            if language in language_mapping:
                return language_mapping[language]
            
            # Check if response contains a valid language
            valid_languages = [
                "python", "javascript", "java", "csharp", "cpp", "typescript", 
                "go", "rust", "kotlin", "swift", "php", "ruby", "scala", "dart",
                "r", "matlab", "sql", "html", "css", "bash", "powershell", 
                "yaml", "json", "xml", "objectivec", "perl", "lua", "haskell",
                "clojure", "erlang", "elixir", "f#", "fsharp", "vb", "vbnet",
                "cobol", "fortran", "assembly", "asm"
            ]
            
            for lang in valid_languages:
                if lang in language:
                    return lang
            
            # If Gemini detection fails, fall back to rule-based
            return self.detect_language_fallback(code)
            
        except Exception as e:
            st.warning(f"Gemini language detection failed: {str(e)}. Using fallback method.")
            return self.detect_language_fallback(code)
    
    def detect_language_fallback(self, code: str) -> str:
        """Enhanced fallback language detection with more languages"""
        # Expanded patterns for better detection
        language_patterns = {
            'python': [
                r'\bdef\s+\w+\s*\(', r'\bimport\s+\w+', r'\bfrom\s+\w+\s+import\b',
                r'\bprint\s*\(', r'\bif\s+.*:', r'\bfor\s+.*:', r'\bwhile\s+.*:',
                r'\btry\s*:', r'\bclass\s+\w+.*:', r'\bwith\s+.*:', r'\bexcept\s*.*:',
                r'\belif\s+.*:', r'\bpass\b', r'\bNone\b', r'\bTrue\b', r'\bFalse\b'
            ],
            'javascript': [
                r'\bfunction\s+\w+\s*\(', r'\bconst\s+\w+', r'\blet\s+\w+', r'\bvar\s+\w+',
                r'=>', r'\bconsole\.log\b', r'\bdocument\b', r'\bwindow\b',
                r'\breturn\b', r'{\s*$', r'}\s*$', r'\bnew\s+\w+', r'\bthis\.',
                r'\bfunction\s*\(', r'\b(null|undefined)\b'
            ],
            'typescript': [
                r'\binterface\s+\w+', r'\btype\s+\w+\s*=', r':\s*(string|number|boolean)',
                r'\bexport\s+interface', r'\bimport\s+.*\bfrom\b', r'<.*>',
                r'\bgeneric\b', r'\bnamespace\s+\w+'
            ],
            'java': [
                r'\bpublic\s+class\s+\w+', r'\bpublic\s+static\s+void\s+main',
                r'\bprivate\s+\w+', r'\bprotected\s+\w+', r'\bSystem\.out\.println',
                r'\bvoid\s+\w+\s*\(', r'\bString\s+\w+', r'\bint\s+\w+', r'\bboolean\s+\w+',
                r'\bpublic\s+\w+\s+\w+\s*\(', r'\bthrows\s+\w+', r'\bextends\s+\w+',
                r'\bimplements\s+\w+', r'\bpackage\s+[\w.]+;'
            ],
            'csharp': [
                r'\busing\s+System', r'\bnamespace\s+\w+', r'\bpublic\s+class\s+\w+',
                r'\bpublic\s+static\s+void\s+Main', r'\bConsole\.WriteLine',
                r'\bprivate\s+\w+', r'\bpublic\s+\w+', r'\bprotected\s+\w+',
                r'\bstring\s+\w+', r'\bint\s+\w+', r'\bbool\s+\w+', r'\bvar\s+\w+\s*=',
                r'\bnew\s+\w+\s*\(', r'\bget\s*;', r'\bset\s*;', r'\bthis\.',
                r'\boverride\s+\w+', r'\bvirtual\s+\w+', r'\babstract\s+\w+'
            ],
            'cpp': [
                r'\b#include\s*<.*>', r'\bstd::', r'\bint\s+main\s*\(',
                r'\bcout\s*<<', r'\bcin\s*>>', r'\bnamespace\s+\w+',
                r'\busing\s+namespace\s+std', r'\bclass\s+\w+', r'\bpublic\s*:',
                r'\bprivate\s*:', r'\bprotected\s*:', r'\bvirtual\s+\w+',
                r'\btemplate\s*<.*>', r'\btypedef\s+\w+'
            ],
            'go': [
                r'\bpackage\s+main', r'\bfunc\s+main\s*\(\)', r'\bfunc\s+\w+\s*\(',
                r'\bimport\s+\(', r'\bfmt\.Print', r'\bvar\s+\w+\s+\w+',
                r'\btype\s+\w+\s+struct', r'\bgo\s+\w+\s*\(', r'\bchan\s+\w+',
                r'\brange\s+\w+', r'\bdefer\s+\w+', r'\binterface\s*{'
            ],
            'rust': [
                r'\bfn\s+main\s*\(\)', r'\bfn\s+\w+\s*\(', r'\blet\s+\w+',
                r'\blet\s+mut\s+\w+', r'\bprintln!\s*\(', r'\buse\s+\w+',
                r'\bstruct\s+\w+', r'\bimpl\s+\w+', r'\btrait\s+\w+',
                r'\bmatch\s+\w+', r'\bSome\s*\(', r'\bNone\b', r'\bResult\s*<'
            ],
            'php': [
                r'<\?php', r'\$\w+', r'\becho\s+', r'\bprint\s+',
                r'\bfunction\s+\w+\s*\(', r'\bclass\s+\w+', r'\bpublic\s+function',
                r'\bprivate\s+function', r'\bprotected\s+function', r'\bextends\s+\w+',
                r'\bimplements\s+\w+', r'\bnew\s+\w+\s*\('
            ],
            'ruby': [
                r'\bdef\s+\w+', r'\bclass\s+\w+', r'\bmodule\s+\w+',
                r'\bputs\s+', r'\bprint\s+', r'\bbegin\b', r'\brescue\b',
                r'\bensure\b', r'\bend\b', r'\bif\s+.*\bthen\b', r'\bunless\s+',
                r'\bcase\s+', r'\bwhen\s+', r'@\w+', r'@@\w+'
            ],
            'kotlin': [
                r'\bfun\s+main\s*\(', r'\bfun\s+\w+\s*\(', r'\bval\s+\w+',
                r'\bvar\s+\w+', r'\bclass\s+\w+', r'\bobject\s+\w+',
                r'\bdata\s+class', r'\bsealed\s+class', r'\bwhen\s*\(',
                r'\bprintln\s*\(', r'\bcompanion\s+object'
            ],
            'swift': [
                r'\bfunc\s+\w+\s*\(', r'\bvar\s+\w+\s*:', r'\blet\s+\w+\s*:',
                r'\bclass\s+\w+', r'\bstruct\s+\w+', r'\benum\s+\w+',
                r'\bprotocol\s+\w+', r'\bextension\s+\w+', r'\bprint\s*\(',
                r'\bif\s+let\s+', r'\bguard\s+let', r'\bswitch\s+\w+'
            ],
            'scala': [
                r'\bobject\s+\w+', r'\bdef\s+main\s*\(', r'\bdef\s+\w+\s*\(',
                r'\bval\s+\w+', r'\bvar\s+\w+', r'\bclass\s+\w+', r'\btrait\s+\w+',
                r'\bcase\s+class', r'\bcase\s+object', r'\bmatch\s*\{',
                r'\bprintln\s*\(', r'\bimport\s+scala'
            ],
            'dart': [
                r'\bvoid\s+main\s*\(', r'\bclass\s+\w+', r'\bString\s+\w+',
                r'\bint\s+\w+', r'\bdouble\s+\w+', r'\bbool\s+\w+',
                r'\bprint\s*\(', r'\bfinal\s+\w+', r'\bconst\s+\w+',
                r'\bextends\s+\w+', r'\bimplements\s+\w+', r'\basync\s+\w+'
            ],
            'r': [
                r'\blibrary\s*\(', r'\brequire\s*\(', r'\bfunction\s*\(',
                r'\bdata\.frame\s*\(', r'\bc\s*\(', r'\blist\s*\(',
                r'\bggplot\s*\(', r'\baes\s*\(', r'\bsummary\s*\(',
                r'<-', r'\bprint\s*\(', r'\bcat\s*\('
            ],
            'matlab': [
                r'\bfunction\s+.*=\s*\w+\s*\(', r'\bend\s*$', r'\bdisp\s*\(',
                r'\bfprintf\s*\(', r'\bplot\s*\(', r'\bfigure\s*\(',
                r'\bhold\s+on', r'\bhold\s+off', r'%.*$', r'\bclc\b', r'\bclear\b'
            ],
            'sql': [
                r'\bSELECT\s+.*\bFROM\b', r'\bINSERT\s+INTO\b', r'\bUPDATE\s+.*\bSET\b',
                r'\bDELETE\s+FROM\b', r'\bCREATE\s+TABLE\b', r'\bDROP\s+TABLE\b',
                r'\bALTER\s+TABLE\b', r'\bWHERE\s+', r'\bORDER\s+BY\b',
                r'\bGROUP\s+BY\b', r'\bHAVING\s+', r'\bJOIN\s+.*\bON\b'
            ],
            'html': [
                r'<!DOCTYPE\s+html>', r'<html.*>', r'<head.*>', r'<body.*>',
                r'<div.*>', r'<span.*>', r'<p.*>', r'<a\s+href=',
                r'<img\s+src=', r'<script.*>', r'<style.*>', r'<link.*>'
            ],
            'css': [
                r'[\w-]+\s*\{', r'[\w-]+\s*:\s*[^;]+;', r'@import\s+',
                r'@media\s+', r'@keyframes\s+', r'#[\w-]+\s*\{',
                r'\.[\w-]+\s*\{', r'color\s*:', r'background\s*:',
                r'margin\s*:', r'padding\s*:', r'font-size\s*:'
            ],
            'bash': [
                r'#!/bin/bash', r'#!/bin/sh', r'\becho\s+', r'\bif\s+\[',
                r'\bfi\b', r'\bfor\s+\w+\s+in\b', r'\bdone\b', r'\bwhile\s+\[',
                r'\bfunction\s+\w+\s*\(', r'\$\w+', r'\$\{.*\}', r'\bexport\s+'
            ],
            'powershell': [
                r'\$\w+', r'\bWrite-Host\b', r'\bGet-\w+', r'\bSet-\w+',
                r'\bNew-\w+', r'\bRemove-\w+', r'\bInvoke-\w+', r'\bTest-\w+',
                r'\bif\s*\(.*\)\s*\{', r'\bforeach\s*\(', r'\bparam\s*\(',
                r'\bfunction\s+\w+\s*\{', r'\[string\]', r'\[int\]'
            ],
            'yaml': [
                r'^\s*\w+\s*:', r'^\s*-\s+\w+', r'---\s*$', r'^\s*#.*',
                r'^\s*\w+\s*:\s*\|', r'^\s*\w+\s*:\s*>', r'^\s*\w+\s*:\s*\[',
                r'version\s*:', r'apiVersion\s*:', r'kind\s*:'
            ],
            'json': [
                r'^\s*\{', r'^\s*\[', r'"\w+"\s*:\s*', r'"\w+"\s*:\s*"',
                r'"\w+"\s*:\s*\d+', r'"\w+"\s*:\s*true', r'"\w+"\s*:\s*false',
                r'"\w+"\s*:\s*null', r'^\s*\}', r'^\s*\]'
            ],
            'xml': [
                r'<\?xml\s+version=', r'<\w+.*?>', r'</\w+>', r'<\w+\s+.*?/>',
                r'<!\[CDATA\[', r'<!--.*?-->', r'<!\s*DOCTYPE\s+',
                r'xmlns\s*=', r'<\w+:\w+.*?>'
            ]
        }
        
        # Count matches for each language
        scores = {}
        for lang, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, code, re.MULTILINE | re.IGNORECASE)
                score += len(matches)
            scores[lang] = score
        
        # Return language with highest score, default to python if no matches
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return 'python'  # Default fallback
    
    def detect_language(self, code: str) -> str:
        """Main language detection method - uses Gemini first, then fallback"""
        return self.detect_language_with_gemini(code)
    
    def split_code_into_functions(self, code: str) -> List[Tuple[str, str]]:
        """Split code into minimal logical blocks to reduce API calls"""
        # For free tier, limit to max 2 blocks to avoid overloading
        functions = []
        lines = code.split('\n')
        
        # Look for major function/class definitions only
        major_blocks = []
        current_block = []
        
        for line in lines:
            stripped = line.strip()
            
            # Detect major function/class definitions for multiple languages
            if (re.match(r'^\s*def\s+(\w+)', line) or  # Python
                re.match(r'^\s*class\s+(\w+)', line) or  # Python, Java, C#
                re.match(r'^\s*function\s+(\w+)', line) or  # JavaScript
                re.match(r'^\s*public\s+class\s+(\w+)', line) or  # Java, C#
                re.match(r'^\s*public\s+static\s+\w+\s+(\w+)', line) or  # Java, C#
                re.match(r'^\s*namespace\s+(\w+)', line) or  # C#
                re.match(r'^\s*using\s+System', line) or  # C#
                re.match(r'^\s*package\s+[\w.]+', line) or  # Java
                re.match(r'^\s*func\s+(\w+)', line) or  # Go, Swift
                re.match(r'^\s*fn\s+(\w+)', line)):  # Rust
                
                # Save previous block if exists and is substantial
                if current_block and len('\n'.join(current_block).strip()) > 50:
                    major_blocks.append('\n'.join(current_block))
                
                # Start new block
                current_block = [line]
            else:
                current_block.append(line)
        
        # Add the last block
        if current_block:
            major_blocks.append('\n'.join(current_block))
        
        # Limit to maximum 2 blocks for free tier
        if len(major_blocks) > 2:
            # Combine smaller blocks
            first_half = major_blocks[:len(major_blocks)//2]
            second_half = major_blocks[len(major_blocks)//2:]
            
            functions.append(("first_section", '\n'.join(first_half)))
            functions.append(("second_section", '\n'.join(second_half)))
        else:
            for i, block in enumerate(major_blocks):
                if len(block.strip()) > 10:  # Only include substantial blocks
                    functions.append((f"section_{i+1}", block))
        
        return functions if functions else [("main_code", code)]
    
    def explain_code_with_gemini(self, code: str, language: str, is_full_code: bool = True) -> str:
        """Generate concise explanation using Gemini API"""
        
        if is_full_code:
            # For full code, use comprehensive prompt
            prompt = f"""Explain this {language} code concisely:

{code}

Provide: 1) What it does, 2) Key components, 3) How it works. Keep it under 200 words."""
        else:
            # For code blocks, use simpler prompt
            prompt = f"""Briefly explain this {language} code section:

{code}

What does this part do? Keep it short and clear."""

        explanation = self.query_gemini(prompt, max_tokens=800)
        
        # If explanation has errors, use fallback
        if "Error" in explanation or len(explanation) < 20:
            return self.explain_code_block_simple(code, language)
        
        return explanation
    
    def explain_code_block_simple(self, code: str, language: str = "python") -> str:
        """Generate explanation using rule-based approach as fallback"""
        explanation = f"**{language.title()} Code Analysis:**\n\n"
        
        lines = code.split('\n')
        key_features = []
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                continue
            
            # Enhanced pattern matching for multiple languages
            patterns = {
                'function': [r'^\s*def\s+(\w+)', r'^\s*function\s+(\w+)', r'^\s*func\s+(\w+)', r'^\s*fn\s+(\w+)'],
                'class': [r'^\s*class\s+(\w+)', r'^\s*public\s+class\s+(\w+)'],
                'variable': [r'^\s*(\w+)\s*=', r'^\s*let\s+(\w+)', r'^\s*var\s+(\w+)', r'^\s*const\s+(\w+)'],
                'conditional': [r'^\s*if\s+', r'^\s*elif\s+', r'^\s*else\s*:', r'^\s*switch\s+'],
                'loop': [r'^\s*for\s+', r'^\s*while\s+', r'^\s*foreach\s+'],
                'error_handling': [r'^\s*try\s*:', r'^\s*catch\s*', r'^\s*except\s*', r'^\s*finally\s*'],
                'return': [r'^\s*return\s+'],
                'import': [r'^\s*import\s+', r'^\s*from\s+.*import', r'^\s*using\s+', r'^\s*#include'],
                'output': [r'^\s*print\s*\(', r'^\s*console\.log', r'^\s*Console\.WriteLine', r'^\s*println!']
            }
            
            # Check patterns
            for feature_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, line):
                        if feature_type == 'function':
                            match = re.search(pattern, line)
                            if match:
                                key_features.append(f"**Function Definition**: Defines `{match.group(1)}()` function")
                        elif feature_type == 'class':
                            match = re.search(pattern, line)
                            if match:
                                key_features.append(f"**Class Definition**: Defines `{match.group(1)}` class")
                        elif feature_type == 'variable':
                            match = re.search(pattern, line)
                            if match:
                                key_features.append(f"**Variable Assignment**: Creates/assigns variable `{match.group(1)}`")
                        elif feature_type == 'conditional':
                            key_features.append("**Conditional Logic**: Contains conditional statement for decision making")
                        elif feature_type == 'loop':
                            key_features.append("**Loop Structure**: Uses loop for iteration")
                        elif feature_type == 'error_handling':
                            key_features.append("**Error Handling**: Implements error handling mechanism")
                        elif feature_type == 'return':
                            key_features.append("**Return Statement**: Returns value from function")
                        elif feature_type == 'import':
                            key_features.append("**Module Import**: Imports external libraries/modules")
                        elif feature_type == 'output':
                            key_features.append("**Output**: Displays information to console")
                        break
        
        # Format the features
        if key_features:
            # Remove duplicates while preserving order
            unique_features = []
            for feature in key_features:
                if feature not in unique_features:
                    unique_features.append(feature)
            explanation += "\n".join(f"• {feature}" for feature in unique_features)
        else:
            explanation += "• Contains basic programming logic and statements"
        
        return explanation
    
    def generate_inline_comments(self, code: str, language: str) -> str:
        """Generate inline comments using simple prompt"""
        
        prompt = f"""Add brief comments to this {language} code:

{code}

Add appropriate comments for important lines only. Keep comments short and use the correct comment syntax for {language}."""

        commented_code = self.query_gemini(prompt, max_tokens=1000)
        
        # If Gemini fails, use rule-based approach
        if "Error" in commented_code or len(commented_code) < len(code):
            return self._generate_comments_rule_based(code, language)
        
        return commented_code
    
    
    def _generate_comments_rule_based(self, code: str, language: str) -> str:
        """Generate comments using rule-based approach"""
        lines = code.split('\n')
        commented_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and existing comments
            if not stripped or stripped.startswith('#') or stripped.startswith('//'):
                commented_lines.append(line)
                continue
            
            comment = self._generate_line_comment(stripped, language)
            if comment:
                comment_prefix = "  #" if language == "python" else "  //"
                commented_lines.append(f"{line}{comment_prefix} {comment}")
            else:
                commented_lines.append(line)
        
        return '\n'.join(commented_lines)
    
    def _generate_line_comment(self, line: str, language: str) -> str:
        """Generate a comment for a specific line"""
        # Function definitions
        if re.match(r'^\s*def\s+(\w+)', line):
            func_name = re.match(r'^\s*def\s+(\w+)', line).group(1)
            return f"Define function {func_name}"
        
        # Class definitions
        if re.match(r'^\s*class\s+(\w+)', line):
            class_name = re.match(r'^\s*class\s+(\w+)', line).group(1)
            return f"Define class {class_name}"
        
        # Variable assignments
        if re.match(r'^\s*(\w+)\s*=', line):
            var_name = re.match(r'^\s*(\w+)\s*=', line).group(1)
            return f"Set {var_name} variable"
        
        # Control structures
        if re.match(r'^\s*if\s+', line):
            return "Check condition"
        if re.match(r'^\s*elif\s+', line):
            return "Check alternative condition"
        if re.match(r'^\s*else\s*:', line):
            return "Handle remaining cases"
        if re.match(r'^\s*for\s+', line):
            return "Start loop iteration"
        if re.match(r'^\s*while\s+', line):
            return "Start conditional loop"
        if re.match(r'^\s*try\s*:', line):
            return "Begin error handling"
        if re.match(r'^\s*except\s*.*:', line):
            return "Handle errors"
        if re.match(r'^\s*finally\s*:', line):
            return "Cleanup operations"
        
        # Return and output
        if re.match(r'^\s*return\s+', line):
            return "Return result"
        if re.match(r'^\s*print\s*\(', line):
            return "Display output"
        
        # Imports
        if re.match(r'^\s*import\s+', line):
            return "Import module"
        if re.match(r'^\s*from\s+.*import', line):
            return "Import specific items"
        
        return ""
    
    def explain_code(self, code: str, add_comments: bool = True) -> Dict[str, str]:
        """Main method to explain code using Gemini API with minimal requests"""
        language = self.detect_language(code)
        
        # Limit code blocks to reduce API calls
        code_blocks = self.split_code_into_functions(code)
        
        results = {
            "language": language,
            "overall_explanation": "",
            "block_explanations": {},
            "commented_code": "",
            "original_code": code,
            "model_used": "Gemini 1.5 Flash"
        }
        
        # Single API call for overall explanation
        try:
            results["overall_explanation"] = self.explain_code_with_gemini(code, language, is_full_code=True)
        except Exception as e:
            st.error(f"Error with Gemini API: {str(e)}")
            results["overall_explanation"] = self.explain_code_block_simple(code, language)
        
        # Only explain blocks if there are multiple significant sections
        if len(code_blocks) > 1 and len(code_blocks) <= 3:
            for block_name, block_code in code_blocks:
                if len(block_code.strip()) > 30:  # Only substantial blocks
                    try:
                        # Add delay to avoid rate limiting
                        time.sleep(1)
                        explanation = self.explain_code_with_gemini(block_code, language, is_full_code=False)
                        results["block_explanations"][block_name] = explanation
                    except Exception as e:
                        # Use fallback for errors
                        results["block_explanations"][block_name] = self.explain_code_block_simple(block_code, language)
        
        # Add inline comments if requested (single API call)
        if add_comments:
            try:
                time.sleep(1)  # Rate limiting
                results["commented_code"] = self.generate_inline_comments(code, language)
            except Exception as e:
                results["commented_code"] = self._generate_comments_rule_based(code, language)
        
        return results

# Streamlit App
def main():
    st.title("🤖 Advanced Code Explainer with Gemini AI")
    st.markdown("Get detailed AI-powered code explanations using Google's Gemini API!")
    
    # Sidebar for configuration
    st.sidebar.header("🔧 Configuration")
    
    # API Key status
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        st.sidebar.success("✅ Gemini API Key loaded from environment")
    else:
        st.sidebar.error("❌ Gemini API Key not found in .env file")
        st.error("Please add your GEMINI_API_KEY to the .env file")
        return
    
    # Initialize explainer
    try:
        explainer = GeminiCodeExplainer()
        st.sidebar.success("✅ Connected to Gemini API")
        
    except Exception as e:
        st.sidebar.error(f"❌ Error: {str(e)}")
        return
    
    # Options
    add_comments = st.sidebar.checkbox("💬 Add inline comments", value=False)  # Default to False
    show_block_explanations = st.sidebar.checkbox("📦 Show block-by-block explanations", value=False)  # Default to False
    
    # Rate limiting info
    st.sidebar.info("⚠️ Using free Gemini API - limited requests per minute")
    
    # Language selection (optional override)
    language_override = st.sidebar.selectbox(
        "🔍 Language Override",
        ["Auto-detect", "Python", "JavaScript", "Java", "C++"],
        help="Leave as 'Auto-detect' for automatic language detection"
    )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Input Code")
        
        # Code input
        code_input = st.text_area(
            "Paste your code here:",
            height=400,
            placeholder="def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
        )
        
        # Example codes
        st.markdown("### 📋 Example Codes")
        examples = {
            "Select an example": "",
            "Python - Machine Learning": '''import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = LogisticRegression()
    model.fit(X_train, y_train)
    
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    
    return model, accuracy

# Usage
X = np.random.randn(1000, 4)
y = np.random.randint(0, 2, 1000)
model, acc = train_model(X, y)
print(f"Model accuracy: {acc:.2f}")''',
            
            "Python - Data Analysis": '''import pandas as pd
import matplotlib.pyplot as plt

def analyze_sales_data(csv_file):
    df = pd.read_csv(csv_file)
    
    # Clean data
    df.dropna(inplace=True)
    df['date'] = pd.to_datetime(df['date'])
    
    # Calculate monthly sales
    monthly_sales = df.groupby(df['date'].dt.to_period('M'))['sales'].sum()
    
    # Create visualization
    plt.figure(figsize=(12, 6))
    monthly_sales.plot(kind='line', marker='o')
    plt.title('Monthly Sales Trend')
    plt.xlabel('Month')
    plt.ylabel('Sales ($)')
    plt.grid(True)
    plt.show()
    
    return monthly_sales

# Statistics
def get_sales_stats(df):
    return {
        'total_sales': df['sales'].sum(),
        'avg_sales': df['sales'].mean(),
        'best_month': df['sales'].idxmax()
    }''',
            
            "JavaScript - Web App": '''class TaskManager {
    constructor() {
        this.tasks = [];
        this.nextId = 1;
    }
    
    addTask(title, description) {
        const task = {
            id: this.nextId++,
            title: title,
            description: description,
            completed: false,
            createdAt: new Date()
        };
        
        this.tasks.push(task);
        this.renderTasks();
        return task;
    }
    
    toggleTask(taskId) {
        const task = this.tasks.find(t => t.id === taskId);
        if (task) {
            task.completed = !task.completed;
            this.renderTasks();
        }
    }
    
    renderTasks() {
        const container = document.getElementById('task-list');
        container.innerHTML = '';
        
        this.tasks.forEach(task => {
            const taskElement = document.createElement('div');
            taskElement.className = task.completed ? 'task completed' : 'task';
            taskElement.innerHTML = `
                <h3>${task.title}</h3>
                <p>${task.description}</p>
                <button onclick="taskManager.toggleTask(${task.id})">
                    ${task.completed ? 'Undo' : 'Complete'}
                </button>
            `;
            container.appendChild(taskElement);
        });
    }
}

const taskManager = new TaskManager();'''
        }
        
        example_choice = st.selectbox("Choose an example:", list(examples.keys()))
        
        if example_choice != "Select an example":
            code_input = st.text_area(
                "Example Code:",
                value=examples[example_choice],
                height=300,
                key="example_code"
            )
        
        # Analyze button
        if st.button("🔍 Analyze Code", type="primary"):
            if code_input.strip():
                with st.spinner("🤖 Gemini is analyzing your code..."):
                    try:
                        results = explainer.explain_code(code_input, add_comments)
                        st.session_state.results = results
                        st.success("✅ Analysis complete!")
                    except Exception as e:
                        st.error(f"❌ Error during analysis: {str(e)}")
            else:
                st.warning("⚠️ Please enter some code to analyze!")
    
    with col2:
        st.subheader("🎯 Analysis Results")
        
        if 'results' in st.session_state:
            results = st.session_state.results
            
            # Model and language info
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.info(f"🧠 **Model**: {results['model_used']}")
            with col_info2:
                st.info(f"🔍 **Language**: {results['language'].title()}")
            
            # Overall explanation
            st.subheader("📖 Detailed Explanation")
            if results['overall_explanation']:
                st.markdown(results['overall_explanation'])
            else:
                st.warning("Could not generate explanation. Please check your Gemini API connection.")
            
            # Block explanations
            if show_block_explanations and results['block_explanations']:
                st.subheader("🔧 Block-by-Block Analysis")
                for block_name, explanation in results['block_explanations'].items():
                    with st.expander(f"📦 {block_name}"):
                        st.markdown(explanation)
            
            # Commented code
            if add_comments and results['commented_code']:
                st.subheader("💬 Code with AI-Generated Comments")
                st.code(results['commented_code'], language=results['language'])
            
            # Download options
            st.subheader("📥 Download Results")
            
            # Prepare comprehensive download content
            download_content = f"""# Code Analysis Report
Generated by: {results['model_used']}
Language: {results['language'].title()}
Date: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 📖 Detailed Explanation
{results['overall_explanation']}

## 🔧 Block-by-Block Analysis
"""
            
            for block_name, explanation in results['block_explanations'].items():
                download_content += f"""
### {block_name}
{explanation}
"""
            
            if results['commented_code']:
                download_content += f"""
## 💬 Code with Comments
```{results['language']}
{results['commented_code']}
```
"""
            
            download_content += f"""
## 📄 Original Code
```{results['language']}
{results['original_code']}
```
"""
            
            st.download_button(
                label="📄 Download Complete Analysis",
                data=download_content,
                file_name=f"code_analysis_{time.strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown"
            )
        
        else:
            st.info("👈 Enter your code and click 'Analyze Code' to see detailed results!")
    
    # Footer with enhanced features
    st.markdown("---")
    st.markdown("### 🚀 Enhanced Features")
    
    feature_cols = st.columns(3)
    
    with feature_cols[0]:
        st.markdown("""
        **🧠 AI-Powered Analysis**
        - Google Gemini 1.5 Flash
        - Detailed explanations
        - Context-aware insights
        - Fast response times
        """)
    
    with feature_cols[1]:
        st.markdown("""
        **💬 Smart Comments**
        - AI-generated comments
        - Educational explanations
        - Multiple languages
        - Contextual annotations
        """)
    
    with feature_cols[2]:
        st.markdown("""
        **📊 Comprehensive Reports**
        - Block-by-block analysis
        - Downloadable reports
        - Code structure insights
        - Best practice suggestions
        """)
    
    # API status in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### 🔗 API Information
    - **Model**: Gemini 1.5 Flash
    - **Provider**: Google AI
    - **Status**: Connected ✅
    """)

if __name__ == "__main__":
    main()