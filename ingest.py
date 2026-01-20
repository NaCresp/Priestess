import os
import shutil  
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

DATA_PATH = "./data"
DB_PATH = "./chroma_db"
EMBEDDING_MODEL = "BAAI/bge-m3"

def create_vector_db():
    if os.path.exists(DB_PATH):
        print(f"检测到旧数据库，正在清理 {DB_PATH} ...")
        shutil.rmtree(DB_PATH) 
        print("旧记忆已格式化。")

    print(f"正在扫描 {DATA_PATH} 下的所有 PDF...")
    
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f"文件夹不存在，已创建 {DATA_PATH}。")
        return

    loader = DirectoryLoader(DATA_PATH, glob="**/*.pdf", loader_cls=PyPDFLoader)
    docs = loader.load()
    
    if not docs:
        print("没找到 PDF 文件！")
        return
        
    print(f"共加载 {len(docs)} 页文档。")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)
    print(f"切分完成，共产生 {len(splits)} 个知识块。")

    print("正在重新构建记忆...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    vectorstore = Chroma.from_documents(
        documents=splits, 
        embedding=embeddings,
        persist_directory=DB_PATH 
    )
    
    print(f"注入完成！数据库已更新。")

if __name__ == "__main__":
    create_vector_db()