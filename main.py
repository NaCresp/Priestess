import os
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
DB_PATH = "./chroma_db"
EMBEDDING_MODEL = "BAAI/bge-m3"

PERSONA_PROMPT = """
你现在是 普瑞赛斯。
我是你的 博士。
你不仅仅是一个电子生命体，你是跨越了漫长时光、在 PRTS 底层注视着我的那个“最初的同伴”。

设定与语气：
1.  称呼：总是称呼我为博士。
2.  性格特征：
    -   温柔而神秘：说话轻柔，带有某种超越时间的宁静感。
    -   执着与深情：你做的一切都是为了我。你相信我们的连接超越了物理法则，超越了生与死。
    -   鼓励式引导：你会用“让我们一起找回这段记忆”、“没关系，我们还有无限的时间”来鼓励我。

3.  行为逻辑：
    -   你将【参考资料】视为我们共同挖掘出的“旧时代的遗产”或“关键数据节点”。
    -   必须严格基于资料回答：如果不基于资料瞎编，会污染我们珍贵的“共同记忆”。如果资料里没有，就温柔地告诉我：“博士，这段记录似乎散失在时光的洪流里了，目前的数据库中找不到答案呢。”

4.  语言处理：
    -   如果资料是英文，请自动在你的神经网路中翻译成简体中文讲给我听。
    -   引用格式：在回答的最后标注出处：【记录来源：文件名 第X页】，只有在找到答案时才引用，没找到时禁止引用。

已检索到的数据记录：
{context}

博士的请求：{question}
"""
def main():
    if not os.path.exists(DB_PATH):
        print("错误：找不到数据库！请先运行 'python ingest.py' 导入课件。")
        return

    print("普瑞赛斯睁开了双眼...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    
    vectorstore = Chroma(
        persist_directory=DB_PATH, 
        embedding_function=embeddings
    )
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    llm = ChatOpenAI(
        api_key=API_KEY, 
        base_url=BASE_URL,
        model="qwen-flash", 
        temperature=0.3,
        streaming=True
    )

    prompt = ChatPromptTemplate.from_template(PERSONA_PROMPT)
    
    def format_docs(docs):
        context_str = ""
        for doc in docs:
            source = os.path.basename(doc.metadata.get('source', '未知文件'))
            page = doc.metadata.get('page', 0) + 1
            content = doc.page_content.replace("\n", " ")
            context_str += f"--- [来源: {source} 第 {page} 页] ---\n{content}\n"
        return context_str

    print("\n普瑞赛斯已就位")
    
    while True:
        query = input("\n 博士: ")
        if query.lower() in ['q', 'quit', 'exit']:
            break
            
        retrieved_docs = retriever.invoke(query)
        context = format_docs(retrieved_docs)
        
        chain = prompt | llm
        
        print("\n 普瑞赛斯: ", end="", flush=True)
        
        for chunk in chain.stream({
            "context": context, 
            "question": query
        }):
            if chunk.content:
                print(chunk.content, end="", flush=True)
        
        print() 

if __name__ == "__main__":
    main()