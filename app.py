import os
import time
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

from main import GeminiCodeExplainer  # Adjust import to your actual file/module


def simulate_evaluation_metrics():
    return {
        "Accuracy": 0.87,
        "F1 Score": 0.90,
        "Precision": 0.93,
        "Recall": 0.85
    }


def plot_metrics(metrics):
    fig, ax = plt.subplots(figsize=(5, 3))
    sns.barplot(x=list(metrics.keys()), y=list(metrics.values()), palette='viridis', ax=ax)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score")
    ax.set_title("🔬 Simulated Evaluation Metrics", fontweight='bold')
    st.pyplot(fig)


def plot_confusion_matrix():
    conf_matrix = np.array([[50, 5], [3, 42]])
    fig, ax = plt.subplots(figsize=(4, 4))
    sns.heatmap(conf_matrix, annot=True, fmt="d", cmap="Blues", xticklabels=["Pred 0", "Pred 1"],
                yticklabels=["True 0", "True 1"], ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("📊 Confusion Matrix (Simulated)", fontweight='bold')
    st.pyplot(fig)


def main():
    st.set_page_config(page_title="Code Explainer with Gemini", layout="wide")
    st.title("🤖 Advanced Code Explainer with Gemini AI")

    # Load API Key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        st.sidebar.error("❌ Gemini API Key not found in `.env` file")
        return

    # Initialize Gemini Explainer
    try:
        explainer = GeminiCodeExplainer()
    except Exception as e:
        st.error(f"❌ Failed to initialize Gemini: {str(e)}")
        return

    # Sidebar options
    st.sidebar.header("🔧 Options")
    add_comments = st.sidebar.checkbox("💬 Add inline comments")
    show_blocks = st.sidebar.checkbox("📦 Show block explanations")
    language_override = st.sidebar.selectbox(
        "🧠 Language",
        ["Auto-detect", "Python", "JavaScript", "Java", "C++"]
    )

    # Input area
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("📝 Input Code")
        default_code = '''def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)'''
        code_input = st.text_area("Paste your code here:", default_code, height=300)

        if st.button("🔍 Analyze Code"):
            if not code_input.strip():
                st.warning("⚠️ Please enter valid code.")
                return

            with st.spinner("Analyzing with Gemini..."):
                try:
                    results = explainer.explain_code(code_input)
                    if add_comments:
                        lang = results.get("language", "python")
                        results["commented_code"] = explainer.generate_inline_comments(code_input, lang)
                    st.session_state["results"] = results
                    st.success("✅ Analysis complete!")
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
                    return

    # Output display
    with col2:
        st.subheader("🎯 Analysis Results")
        if "results" not in st.session_state:
            st.info("👈 Enter your code and click 'Analyze Code'")
            return

        results = st.session_state["results"]
        st.markdown(f"🧠 **Model Used**: {results.get('model_used', 'N/A')}")
        st.markdown(f"🗣️ **Language**: {results.get('language', 'unknown').title()}")

        # Overall explanation
        st.subheader("📄 Explanation:")
        if explanation := results.get("overall_explanation"):
            st.markdown(explanation)
        else:
            st.warning("No explanation found.")

        # Block explanations
        if show_blocks and results.get("block_explanations"):
            st.subheader("📦 Block-by-Block Analysis")
            for block, expl in results["block_explanations"].items():
                with st.expander(f"🔹 {block}"):
                    st.markdown(expl)

        # Inline comments
        if add_comments and results.get("commented_code"):
            st.subheader("💬 Code with Inline Comments:")
            st.code(results["commented_code"], language=results["language"])

        # Graphs
        st.subheader("📈 AI Insights (Simulated)")
        plot_metrics(simulate_evaluation_metrics())
        plot_confusion_matrix()

        # Download section
        st.subheader("📥 Download Report")
        download_content = f"""
# Code Analysis Report

**Model**: {results['model_used']}
**Language**: {results['language'].title()}
**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 📖 Explanation
{results['overall_explanation'] or 'No explanation.'}

## 📦 Block Explanations
"""
        for block, exp in results.get("block_explanations", {}).items():
            download_content += f"### {block}\n{exp}\n"

        if results.get("commented_code"):
            download_content += f"\n## 💬 Code with Comments\n```{results['language']}\n{results['commented_code']}\n```\n"

        download_content += f"\n## 📄 Original Code\n```{results['language']}\n{results['original_code']}\n```\n"

        st.download_button("📄 Download Markdown Report", download_content, file_name="analysis.md")


if __name__ == "__main__":
    main()
