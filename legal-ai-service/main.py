from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import faiss
import pickle
import numpy as np
import torch
import re
import html
import time
from sentence_transformers import SentenceTransformer
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from transformers import BartTokenizer, BartForConditionalGeneration

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load BART model
print("🔍 Loading BART model...")
bart_tokenizer = BartTokenizer.from_pretrained("facebook/bart-large-cnn")
bart_model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn").to(device)

# Load embedding model
print("📂 Loading embedding model...")
model = SentenceTransformer("models/legal_embedding_model")

# Load FAISS index and section data
print("📚 Loading FAISS index...")
index = faiss.read_index("models/legal_index.faiss")

print("📚 Loading section data...")
with open("models/legal_sections.pkl", "rb") as f:
    data = pickle.load(f)
    section_data = data['section_data']
    all_acts = data['all_acts']

print("✅ All models loaded successfully!")

class ConversationState:
    def __init__(self):
        self.sessions = {}
        
    def get_session(self, session_id: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'current_context': None,
                'references': None,
                'cases': None,
                'history': []
            }
        return self.sessions[session_id]

    def update(self, session_id: str, query: str, answer: str, references: List[Dict], cases: List[Dict]):
        session = self.get_session(session_id)
        session['current_context'] = {
            'query': query,
            'answer': answer,
            'references': references,
            'cases': cases
        }
        session['references'] = references
        session['cases'] = cases
        session['history'].append(('user', query))
        session['history'].append(('assistant', answer))

conv_state = ConversationState()

def sanitize_query(query: str) -> str:
    query = html.escape(query.strip())
    return re.sub(r'\s+', ' ', query)

def find_relevant_sections(query: str, k: int = 5) -> List[Dict]:
    query_embedding = model.encode([query])
    D, I = index.search(query_embedding, k)
    return [{
        'act': section_data[idx]['act'],
        'section_number': section_data[idx]['section_number'],
        'text': section_data[idx]['full_text'],
        'score': D[0][i]
    } for i, idx in enumerate(I[0])]

def generate_with_bart(input_text: str, max_length: int = 150) -> str:
    try:
        inputs = bart_tokenizer(
            input_text,
            max_length=1024,
            truncation=True,
            return_tensors="pt"
        ).to(device)
        
        summary_ids = bart_model.generate(
            inputs.input_ids,
            max_length=max_length,
            num_beams=4,
            early_stopping=True
        )
        
        return bart_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    except Exception as e:
        print(f"BART generation error: {e}")
        return ""

def generate_direct_answer(query: str, context: str = "") -> str:
    input_text = f"Generate 3 legal steps for: {query}. Context: {context}" if context else f"Legal steps for: {query}"
    steps = generate_with_bart(input_text, 200)
    return steps if steps else "Immediate legal steps:"

def generate_legal_analysis(text: str, act_name: str, section_number: str) -> Dict:
    input_text = f"Explain in one line: {act_name} Section {section_number} - {text[:1000]}"
    summary = generate_with_bart(input_text, 100)
    return {'summary': summary}

def fetch_kanoon_results(query: str, max_results: int = 3) -> List[Dict]:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://indiankanoon.org/")
        search_box = driver.find_element(By.ID, "search-box")
        search_box.send_keys(query + Keys.RETURN)
        time.sleep(3)
        return [{
            "title": r.text[:80],
            "url": r.get_attribute("href")
        } for r in driver.find_elements(By.CSS_SELECTOR, "div.result_title > a")[:max_results]]
    except Exception as e:
        print(f"Kanoon error: {e}")
        return []
    finally:
        if driver: driver.quit()

def is_follow_up(query: str, session: dict) -> bool:
    if not session.get('current_context'):
        return False

    follow_up_indicators = [
        'follow up', 'previous', 'explain', 'more info', 'about that'
    ]
    return any(indicator in query.lower() for indicator in follow_up_indicators)

def format_response(base_answer: str, references: List[Dict], cases: List[Dict]) -> str:
    # Process steps
    steps = [line.strip() for line in base_answer.split('\n') if line.strip()]
    
    response = "🚨 Immediate Steps:\n" + "\n".join(f"- {step}" for step in steps[:3])
    
    # Legal provisions
    response += "\n\n⚖️ Relevant Provisions:"
    for ref in references[:3]:
        response += f"\n- {ref['act']} Sec {ref['section_number']}: {ref['summary']}"
    
    # Generate recommendations
    rec_text = generate_with_bart("Generate 3 legal recommendations: " + base_answer, 150)
    recommendations = [line.strip() for line in rec_text.split('\n') if line.strip()]
    
    response += "\n\n📌 Key Recommendations:" 
    for rec in recommendations[:3]:
        response += f"\n- {rec}"

    # Case law
    if cases:
        response += "\n\n🔗 Related Cases:"
        for case in cases[:2]:
            response += f"\n- {case['title'][:50]} ({case['url']})"
    
    return response

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessQueryRequest(BaseModel):
    query: str
    session_id: str = "default"

class ResponseModel(BaseModel):
    answer: str
    references: List[Dict]
    cases: List[Dict]
    is_follow_up: bool
    session_id: str

@app.post("/process-query", response_model=ResponseModel)
async def process_legal_query(request: ProcessQueryRequest):
    try:
        session = conv_state.get_session(request.session_id)
        query = sanitize_query(request.query)
        
        if len(query) < 3:
            raise HTTPException(status_code=400, detail="Please ask a more detailed question.")

        if is_follow_up(query, session):
            context = "\n".join([
                f"Previous: {session['current_context']['query']}",
                f"Answer: {session['current_context']['answer']}"
            ])
            answer = generate_direct_answer(query, context)
            return ResponseModel(
                answer=answer,
                references=session['references'],
                cases=session['cases'],
                is_follow_up=True,
                session_id=request.session_id
            )

        sections = find_relevant_sections(query)
        if not sections:
            raise HTTPException(status_code=404, detail="No relevant laws found")

        context = "\n".join(f"{s['act']} Section {s['section_number']}: {s['text']}" 
                      for s in sections[:2])
        
        base_answer = generate_direct_answer(query, context)
        references = []
        
        for s in sections[:2]:
            analysis = generate_legal_analysis(s['text'], s['act'], s['section_number'])
            references.append({
                'act': s['act'],
                'section_number': s['section_number'],
                **analysis,
                'full_text': s['text'][:300] + '...'
            })

        cases = fetch_kanoon_results(query)
        formatted_answer = format_response(base_answer, references, cases)

        conv_state.update(request.session_id, query, formatted_answer, references, cases)
        
        return ResponseModel(
            answer=formatted_answer,
            references=references,
            cases=cases,
            is_follow_up=False,
            session_id=request.session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)