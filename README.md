# Contract-Compliance-Assistant

An AI-powered Retrieval-Augmented Generation (RAG) application that helps organizations validate contracts against internal policies and compliance requirements.


## Overview

The Contract Compliance Assistant assists users in reviewing contracts and related documents by retrieving relevant information from organizational policies, SOPs, knowledge articles, and historical records. The system provides evidence-based compliance checks and highlights potential issues before contract approval.

This project is currently in the initial development phase.

## Planned Features

- Contract validation against company policies
- Detection of missing or conflicting clauses
- Invoice validation against approved contracts
- Policy-based question answering
- Explainable AI responses with supporting evidence
- ServiceNow incident lookup for similar compliance issues

---

## 1. Project Setup

Clone the repository:

```bash
git clone https://github.com/suhas859/Contract-Compliance-Assistant
cd contract-compliance-assistant
```

create virtual env :

```bash
python3 -m venv venv
source venv/bin/activate
```

Install Dependencies

```bash
pip install -r requirements.txt
```

Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Pull Required Models


```bash
ollama pull llama3
```


