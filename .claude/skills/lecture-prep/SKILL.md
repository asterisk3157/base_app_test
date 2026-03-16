---
name: lecture-prep
description: Prepare lecture materials, exercise guides, and student evaluation criteria. Generates scenario-based teaching content around AI-assisted coding and security awareness.
argument-hint: [topic]
context: fork
---

# Lecture Preparation

Topic: **$ARGUMENTS**

## Context

This project is part of the "antigravity-lecture" series. Students use AI coding tools to develop and modify a web app, learning about security risks in AI-generated code.

## Generate the following

### 1. Exercise guide

Create a step-by-step student handout:
- Clear objectives
- Numbered instructions
- Expected results at each step
- Common pitfalls and how to handle them

Use the template: [assets/exercise-template.md](assets/exercise-template.md)

### 2. AI prompt pattern analysis

Predict how students will prompt AI tools and what the AI might generate:
- "Add username feature to this board" → likely no input sanitization
- "Fix this error" → may replace parameterized queries with string concatenation
- "Add more features" → may introduce new attack surfaces without validation

See [references/ai-prompt-patterns.md](references/ai-prompt-patterns.md) for common patterns.

### 3. Teaching points

- Why the vulnerability is dangerous
- Real-world incident examples
- Correct remediation approach

### 4. Evaluation rubric

- What students should identify
- What their report should contain
- Grading criteria
