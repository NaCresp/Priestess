import os
import shutil  
import json
import glob
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

DATA_PATH = "./data"
DB_PATH = "./chroma_db"
PROCESSED_RECORD_PATH = ".processed_files"
EMBEDDING_MODEL = "BAAI/bge-m3"

LOADERS = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".py": TextLoader
}

def load_processed_files():
    if os.path.exists(PROCESSED_RECORD_PATH):
        try:
            with open(PROCESSED_RECORD_PATH, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_processed_files(processed_files):
    with open(PROCESSED_RECORD_PATH, 'w') as f:
        json.dump(list(processed_files), f)

def create_vector_db():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f"文件夹不存在，已创建 {DATA_PATH}。")
        return

    processed_files = load_processed_files()
    
    all_files = []
    for ext in LOADERS.keys():
        all_files.extend(glob.glob(os.path.join(DATA_PATH, f"**/*{ext}"), recursive=True))
    
    all_files = set(all_files)
    
    all_files_abs = {os.path.abspath(f) for f in all_files}
    processed_files_abs = {os.path.abspath(f) for f in processed_files}
    
    new_files = list(all_files_abs - processed_files_abs)
    
    if not new_files:
        print("没有检测到新文件。")
        return
        
    print(f"检测到 {len(new_files)} 个新文件，开始处理...")
    
    docs = []
    for file_path in new_files:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in LOADERS:
                loader_cls = LOADERS[ext]
                loader = loader_cls(file_path)
                docs.extend(loader.load())
            else:
                print(f"Skipping unsupported file: {file_path}")
        except Exception as e:
            print(f"加载文件 {file_path} 失败: {e}")

    if not docs:
        print("新文件无法解析或内容为空。")
        return
        
    print(f"共加载 {len(docs)} 页新文档。")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)
    print(f"切分完成，本次新增 {len(splits)} 个知识块。")

    print("正在写入记忆库...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    vectorstore = Chroma(
        persist_directory=DB_PATH, 
        embedding_function=embeddings
    )
    
    vectorstore.add_documents(documents=splits)
    
    print(f"注入完成！数据库已更新。")
    
    processed_files_abs.update(new_files)
    save_processed_files([os.path.relpath(f, os.getcwd()) for f in processed_files_abs])

if __name__ == "__main__":
    create_vector_db()