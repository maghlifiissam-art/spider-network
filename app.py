import os
import streamlit as st
from groq import Groq

st.set_page_config(page_title="Spider Network", page_icon="🕷️", layout="wide")

st.title("🕷️ Spider Network Operations")

api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    st.error("⚠️ GROQ_API_KEY is missing in Streamlit Secrets!")
    st.stop()

client = Groq(api_key=api_key)

tab1, tab2 = st.tabs(["🚀 Fast Lane", "🛡️ Guarded Lane"])

with tab1:
    st.subheader("Spider Tasks Management")
    
    spider_type = st.radio(
        "Select Spider Type:",
        ["Affiliate Spider", "Media Spider", "Digital Products Spider"]
    )
    
    task_prompt = st.text_area("Task Description or Target Product:", placeholder="Enter task details here...")
    
    if st.button("Run Spider 🚀"):
        if not task_prompt.strip():
            st.warning("Please enter the task description first.")
        else:
            with st.spinner("Processing generation via Groq..."):
                try:
                    completion = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                            {
                                "role": "system",
                                "content": f"You are a professional expert working in the Spider Network under the {spider_type} module. Provide accurate, well-organized, and professional responses in Arabic."
                            },
                            {
                                "role": "user",
                                "content": task_prompt
                            }
                        ],
                        temperature=0.7,
                        max_tokens=2048
                    )
                    
                    result_text = completion.choices[0].message.content
                    st.success("Task completed successfully!")
                    st.markdown("### Generated Results:")
                    st.write(result_text)
                    
                except Exception as e:
                    st.error(f"Execution failed: {e}")

with tab2:
    st.subheader("Strategic Supervision Zone")
    st.info("This section is reserved for sensitive financial and strategic decisions.")
