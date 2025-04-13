import streamlit as st
import requests
import json
import time

# 自動スクロール用のJavaScript関数
def auto_scroll_to_bottom():
    js = """
    <script>
    function scrollToBottom() {
        const mainElement = window.parent.document.querySelector('.main');
        if (mainElement) {
            mainElement.scrollTop = mainElement.scrollHeight;
        }
        
        // モバイル対応
        window.scrollTo(0, document.body.scrollHeight);
    }
    
    // DOMの読み込み完了後に実行
    window.addEventListener('load', function() {
        // 少し遅延させて実行（メッセージが表示された後に実行するため）
        setTimeout(scrollToBottom, 200);
    });
    </script>
    """
    return js

# ソーシャルメニューを非表示にする設定
st.set_page_config(
    page_title="戦国拳法AI師範", 
    page_icon="🥋", 
    layout="wide",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# カスタムCSS - Streamlitのデフォルトの余分な要素を非表示にする
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

st.title("戦国拳法AI師範")
st.markdown("あなたの柔術に関する質問に経験豊富な師範がお答えします。質問を入力してください。")

# Dify APIの設定をsecretsから読み込み
api_key = st.secrets["DIFY_API_KEY"]
api_endpoint = st.secrets.get("DIFY_API_ENDPOINT", "https://api.dify.ai/v1/chat-messages")

# サイドバーに情報を表示
with st.sidebar:
    st.markdown("## 戦国拳法AI師範")
    st.markdown("このアプリはブラジリアン柔術の技術や知識について質問できるAIアシスタントです。")
    st.markdown("---")
    st.markdown("### 質問例:")
    st.markdown("- 三角絞めの基本的なやり方を教えてください")
    st.markdown("- クローズドガードから効果的なスイープを教えてください")
    st.markdown("- 片閂のコツを教えてください")
    st.markdown("- 初心者が最初に覚えるべき技は何ですか？")
    
    # リセットボタン - experimental_rerunをrerunに修正
    if st.button("会話をリセット"):
        st.session_state.messages = []
        st.session_state.conversation_id = ""
        st.rerun()  # 修正: experimental_rerunの代わりにrerunを使用

# チャット履歴の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = ""

# 過去のメッセージを表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザー入力を受け取る
prompt = st.chat_input("質問を入力してください...")

# API呼び出しの関数
def call_dify_api(user_query, api_key, api_endpoint, conversation_id=""):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": {},
        "query": user_query,
        "response_mode": "blocking",
        "conversation_id": conversation_id,
        "user": "user"
    }
    
    # リトライ回数を設定
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # タイムアウトを30秒に設定（必要に応じて調整）
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    "success": True,
                    "answer": response_data.get("answer", "回答を生成できませんでした。"),
                    "conversation_id": response_data.get("conversation_id", "")
                }
            elif response.status_code == 504:
                # タイムアウトエラーの場合はリトライ
                retry_count += 1
                if retry_count < max_retries:
                    # リトライ前に少し待機
                    time.sleep(2)
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"Difyサーバーの応答がタイムアウトしました。しばらく時間をおいて再度お試しください。",
                        "details": response.text
                    }
            else:
                return {
                    "success": False,
                    "error": f"エラーが発生しました。ステータスコード: {response.status_code}",
                    "details": response.text
                }
        except requests.exceptions.Timeout:
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(2)
                continue
            else:
                return {
                    "success": False,
                    "error": "リクエストがタイムアウトしました。しばらく時間をおいて再度お試しください。"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            }

# 送信ボタンがクリックされた場合
if prompt:
    # ユーザーのメッセージを表示
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # AI応答のプレースホルダを作成
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner("回答を生成中..."):
            # APIリクエスト
            response = call_dify_api(
                prompt, 
                api_key, 
                api_endpoint, 
                st.session_state.conversation_id
            )
            
            if response["success"]:
                # 会話IDを保存
                if response.get("conversation_id"):
                    st.session_state.conversation_id = response["conversation_id"]
                
                # 回答を表示
                message_placeholder.markdown(response["answer"])
                st.session_state.messages.append({"role": "assistant", "content": response["answer"]})
            else:
                # エラーメッセージを表示
                message_placeholder.markdown(f"⚠️ {response.get('error', 'エラーが発生しました')}")
                if response.get("details"):
                    with st.expander("詳細エラー情報"):
                        st.code(response["details"])
    
    # 自動スクロールのJavaScriptを挿入
    st.components.v1.html(auto_scroll_to_bottom(), height=0)

# 使い方ガイド
with st.expander("使い方ガイド"):
    st.markdown("""
    ### 使い方
    1. 下部のテキスト入力欄に質問を入力し、Enterキーを押します
    2. AIが回答を生成するまでお待ちください
    3. 会話をリセットしたい場合は、サイドバーの「会話をリセット」ボタンをクリックしてください
    
    ### このアプリについて
    このアプリはブラジリアン柔術に関する知識ベースに基づいて質問に回答します。
    初心者から上級者まで、様々なレベルの質問に対応しています。
    
    ### 注意事項
    - 会話履歴はブラウザのセッション中のみ保持されます
    - 医学的なアドバイスや怪我の診断には使用しないでください
    """)

# フッター (カスタムフッター - Streamlitのデフォルトフッターは非表示)
st.markdown("---")
st.markdown("© 2025 戦国拳法AI師範@Silent柔術 | Powered by Streamlit & Dify") 