src/
|
|── agent/
| |--graph.py
| |--nodes.py
| |--state.py
|
├── routes/
│ ├── chat.py
│ ├── pdf_upload.py
|
|── db/
│── factories/
| |── llm_factory.py
| |── embedding_factory.py
|
├── services/
│ │
│ ├── retrieval/
│ │ ├── retrieval_pipeline.py
│ │ ├── query_parser.py
│ │ ├── fts_search.py
│ │ ├── vector_search.py
│ │ ├── hybrid_merge.py
│ │ └── reranker.py
│ │
│ ├── resume/
│ │ ├── resume_parser.py
│ │ ├── resume_embedding.py
│ │ └── resume_reader.py
│ │ └── resume_upload.py
│ ├── llm/
│ │ ├── prompts.py
│ │ └── response_generator.py
│ │
│ └── streaming/
│ └── chat_stream_service.py
| └── chat/
└── chat_loader.py
|--config.py
|--main.py
