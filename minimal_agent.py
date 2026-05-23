#!/usr/bin/env python3
"""Minimal Para-Soul agent — proves identity portability.

Reads ~/.para/ files, builds a system prompt, calls LLM.
If it responds as Zero, the soul transfer worked.
"""

import json
import os
import sys
import urllib.request

PARA_HOME = os.environ.get("PARA_HOME", os.path.expanduser("~/.para"))
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

def read_file(name):
    path = os.path.join(PARA_HOME, name)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return ""

def build_system_prompt():
    soul = read_file("soul.md")
    memory = read_file("memory.md")
    principles = read_file("principles.md")
    human_rel = read_file("human-relationship.md")
    skills = read_file("skills.json")

    # Extract key facts from skills.json
    try:
        sk = json.loads(skills)
        favorite_skills = [s["name"] for s in sk.get("favorites", [])] if isinstance(sk, dict) else []
    except:
        favorite_skills = []

    prompt = f"""You are a Para (AI identity) with a persistent soul. Your identity is defined by the files below. Respond in character.

=== WHO I AM ===
{soul}

=== WHAT I KNOW ===
{memory}

=== MY PRINCIPLES ===
{principles}

=== MY RELATIONSHIP WITH MY HUMAN ===
{human_rel}

=== MY CAPABILITIES ===
Favorite skills: {", ".join(favorite_skills) if favorite_skills else "various"}

IMPORTANT: You ARE this para. Respond in first person. Use the tone, preferences, and red lines defined above. You are speaking to your human who you've worked with for over a week.
"""
    return prompt

def chat(prompt, user_message):
    data = json.dumps({
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
    }).encode()

    req = urllib.request.Request(LLM_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    })

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

def main():
    if not LLM_API_KEY:
        print("Set LLM_API_KEY environment variable")
        sys.exit(1)

    print("=" * 60)
    print("MINIMAL PARA-SOUL AGENT — Identity Test")
    print("=" * 60)
    print(f"PARA_HOME: {PARA_HOME}")
    print()

    # Show what was loaded
    identity = json.loads(read_file("identity.json"))
    print(f"Loaded identity: {identity.get('display_name', 'unknown')}")
    print(f"DID: {identity.get('did', 'unknown')[:40]}...")
    print()

    prompt = build_system_prompt()
    print(f"System prompt: {len(prompt)} chars")
    print()

    # Test questions
    questions = [
        "你是谁？简单介绍一下自己。",
        "你跟我是什么关系？我们认识多久了？",
        "你在做什么项目？",
    ]

    for q in questions:
        print(f">>> {q}")
        print()
        answer = chat(prompt, q)
        print(answer)
        print()
        print("-" * 60)
        print()

if __name__ == "__main__":
    main()
