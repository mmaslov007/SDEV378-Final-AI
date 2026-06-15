**AI Study Assistant Quiz Generator**  
*Final Project Proposal | Team: Maxwell Maslov, Huma Khomidov*

# **Project Overview**

Our project is an AI-enabled study assistant that turns uploaded course materials into practice quizzes, flashcards, and source-grounded explanations. Users can upload PDFs, images, text files, or pasted notes. The app extracts the text, indexes the content, retrieves relevant sections, and uses a language model to generate original study questions.

The proof of concept will focus on one clean happy path: upload material, generate a quiz, answer questions, and review explanations tied back to the uploaded sources.

# **Problem and Intended Users**

Students often have notes, readings, slides, and handouts spread across different files. This app helps them turn those materials into active recall practice instead of manually writing study questions.

* Users: students preparing for quizzes, midterms, finals, or certification-style exams.  
* Use case: upload notes or readings and generate questions by topic or difficulty.  
* Value: faster studying with explanations connected to source snippets.

# **Core User Flow**

1. Upload or paste study material.  
2. Extract and preview the text.  
3. Chunk and index the content with embeddings.  
4. Choose quiz, flashcards, explanation, or Q\&A mode.  
5. Retrieve source chunks and generate the response.  
6. Display questions, answers, explanations, and snippets.

# **AI Components**

| Component | Tool | Purpose | Main risk |
| :---- | :---- | :---- | :---- |
| OCR / extraction | Tesseract \+ PyMuPDF | Convert files into readable text | Poor scans or tables |
| Embedding search | all-MiniLM-L6-v2 \+ ChromaDB | Find relevant source chunks | Weak matches from vague prompts |
| LLM generation | GroqCloud LLM | Create quizzes and explanations | Rate limits or hallucinations |
| Optional classifier | LLM or local model | Tag topic and difficulty | Incorrect labels |

# **Technical Stack and Cost Plan**

The stack keeps most processing local and free. GroqCloud will be used through our existing account for fast LLM responses. If Groq is unavailable or rate-limited, the app can still extract, index, search, and display source chunks; Ollama may be added as a local fallback.

* UI/backend: Streamlit \+ Python  
* Extraction: PyMuPDF \+ Tesseract OCR  
* Search: sentence-transformers/all-MiniLM-L6-v2 \+ local ChromaDB  
* Generation: GroqCloud LLM, optional Ollama fallback

# **Research Pass**

| Piece | Access / cost | Output | Integration | Failure mode |
| :---- | :---- | :---- | :---- | :---- |
| Tesseract OCR | Free, local | Text from scans/images | pytesseract | Wrong text from poor scans |
| PyMuPDF | Free, local | Text from PDFs | Python package | Scans may return no text |
| all-MiniLM-L6-v2 | Free, local | 384-dim embeddings | sentence-transformers | Weak semantic matches |
| ChromaDB | Free, local | Matching chunks | Python client | Bad chunking hurts search |
| GroqCloud LLM | Existing account; free-tier limits | Questions/explanations | Python SDK or REST | Rate limits or hallucinations |

# 

# 

# **Failure Handling**

* OCR errors: show a preview so users can correct or replace bad text.  
* Weak retrieval: display source snippets and allow a narrower topic.  
* LLM issues: require source-grounded responses and limit question count.  
* Rate limits: keep the app useful by still showing retrieved content.

# **MVP Features**

* Upload or paste study material.  
* Extract and preview text.  
* Index content for semantic search.  
* Generate multiple-choice questions, flashcards, explanations, or open-response Q&A.  
* Show the source snippets used for each response.

# **Happy Path Demo**

We will upload a sample handout or notes file, generate a short quiz, answer one or two questions, and review explanations with source snippets. This demonstrates the full pipeline from document upload to AI-generated study output.

# **Team Responsibilities**

| Team Member 1: UI \+ Documents | Team Member 2: AI Pipeline |
| :---- | :---- |
| Streamlit interface, upload, extraction, OCR fallback, preview, result display. | Chunking, embeddings, ChromaDB search, GroqCloud integration, prompts, failures. |

# **Definition of Success**

The project is successful if the app completes the happy path without crashing and clearly shows three AI components working together: document extraction, semantic retrieval, and LLM-generated study output.