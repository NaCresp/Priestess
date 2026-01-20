import os
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

load_dotenv()

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

class PriestessAI:
    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.db_path = "./chroma_db"
        self.embedding_model = "BAAI/bge-m3"
        self.llm = None
        self.retriever = None
        self.prompt = ChatPromptTemplate.from_template(PERSONA_PROMPT)
        self.init_components()

    def init_components(self):
        if not os.path.exists(self.db_path):
            print("错误：找不到数据库！请先运行 'python ingest.py' 导入课件。")
            return

        print("普瑞赛斯正在唤醒...")
        embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model)
        
        vectorstore = Chroma(
            persist_directory=self.db_path, 
            embedding_function=embeddings
        )
        
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

        self.llm = ChatOpenAI(
            api_key=self.api_key, 
            base_url=self.base_url,
            model="qwen-flash", 
            temperature=0.3,
            streaming=True
        )
        print("普瑞赛斯已就位")

    def format_docs(self, docs):
        context_str = ""
        for doc in docs:
            source = os.path.basename(doc.metadata.get('source', '未知文件'))
            page = doc.metadata.get('page', 0) + 1
            content = doc.page_content.replace("\n", " ")
            context_str += f"--- [来源: {source} 第 {page} 页] ---\n{content}\n"
        return context_str

    def chat(self, query):
        if not self.retriever or not self.llm:
            yield "普瑞赛斯似乎还没准备好..."
            return

        retrieved_docs = self.retriever.invoke(query)
        context = self.format_docs(retrieved_docs)
        
        chain = self.prompt | self.llm
        
        for chunk in chain.stream({
            "context": context, 
            "question": query
        }):
            if chunk.content:
                yield chunk.content

def main():
    ai = PriestessAI()
    
    print("普瑞赛斯睁开了双眼...")
    
    while True:
        query = input("\n 博士: ")
        if query.lower() in ['q', 'quit', 'exit']:
            break
            
        print("\n 普瑞赛斯: ", end="", flush=True)
        
        for content in ai.chat(query):
            print(content, end="", flush=True)
        
        print() 

if __name__ == "__main__":
    main()
    