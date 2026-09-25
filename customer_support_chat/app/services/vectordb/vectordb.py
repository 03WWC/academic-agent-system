import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from customer_support_chat.app.core.settings import get_settings
from customer_support_chat.app.services.utils import get_qdrant_client
from customer_support_chat.app.services.vectordb.chunkenizer import recursive_character_splitting
from customer_support_chat.app.core.logger import logger
from langchain_openai import OpenAIEmbeddings

settings = get_settings()

class VectorDB:
    def __init__(self, collection_name):
        self.collection_name = collection_name
        self.client = get_qdrant_client()
        # 初始化 OpenAI embeddings
        if settings.OPENAI_BASE_URL:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL
            )
        else:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.OPENAI_API_KEY
            )
        self.create_collection()

    def create_collection(self):
        if not self.client.get_collection(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            logger.info(f"已创建新集合：{self.collection_name}")
        else:
            logger.info(f"集合 {self.collection_name} 已存在")

    def generate_embedding(self, content):
        return self.embeddings.embed_query(content)

    def upsert_vector(self, doc_id, chunk_text, embedding, url, chunk_index):
        chunk_id = str(uuid.uuid4())
        payload = {
            "url": url,
            "document_id": str(doc_id),
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
        }

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(id=chunk_id, vector=embedding, payload=payload)
            ]
        )

    def create_embeddings(self, docs):
        for doc_id, content, url in docs:
            if content is None:
                logger.warning(f"文档 {doc_id} 内容为空，已跳过")
                continue

            chunks = recursive_character_splitting(content)
            for i, chunk in enumerate(chunks):
                try:
                    logger.info(f"正在为文档 {doc_id} 的第 {i+1} 个 chunk 生成 embedding")
                    embedding = self.generate_embedding(chunk)
                    self.upsert_vector(doc_id, chunk, embedding, url, i)
                except Exception as e:
                    logger.error(f"为文档 {doc_id} 的第 {i+1} 个 chunk 生成或存储 embedding 失败：{str(e)}")

        logger.info("所有文档的 embedding 生成流程已完成")

    def search(self, query, k=3):
        query_embedding = self.generate_embedding(query)
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=k,
            with_payload=True,
        )
        return search_result
