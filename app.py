import streamlit as st
import requests
import json
import time
import re  # 正規表現を使用するためのライブラリを追加

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

# Claude Sonnetの応答からthinkタグを削除する関数
def remove_think_tags(text):
    # <think>タグとその内容を削除
    cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # 空の行が連続する場合、1行の空行にまとめる
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
    return cleaned_text.strip()

# ソーシャルメニューを非表示にする設定
st.set_page_config(
    page_title="戦国寝技拳法AI師範", 
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

st.title("戦国寝技拳法AI師範")
st.markdown("あなたの柔術に関する質問に経験豊富な師範がお答えします。質問を入力してください。")

# Dify APIの設定をsecretsから読み込み
api_key = st.secrets["DIFY_API_KEY"]
api_endpoint = st.secrets.get("DIFY_API_ENDPOINT", "https://api.dify.ai/v1/chat-messages")

# サイドバーに情報を表示
with st.sidebar:
    st.markdown("## 戦国寝技拳法AI師範")
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
            # 指数バックオフ - リトライ回数に応じて待機時間を増加
            if retry_count > 0:
                # 1回目は2秒、2回目は4秒、3回目は8秒...
                wait_time = 2 ** retry_count
                time.sleep(wait_time)
            
            # タイムアウトを30秒に設定（必要に応じて調整）
            response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    return {
                        "success": True,
                        "answer": response_data.get("answer", "回答を生成できませんでした。"),
                        "conversation_id": response_data.get("conversation_id", "")
                    }
                except Exception as e:
                    # JSONデコードに失敗した場合、レスポンスボディをバイナリとして安全に処理
                    error_text = ""
                    try:
                        # response.textではなくresponse.contentを使用し、明示的にUTF-8でデコード
                        error_text = response.content.decode('utf-8', errors='replace')
                    except:
                        error_text = "レスポンスの文字列化に失敗しました"
                        
                    return {
                        "success": False,
                        "error": f"レスポンスの解析に失敗しました: {str(e)}",
                        "details": error_text
                    }
            # 自動リトライするべきエラーコードの場合
            elif response.status_code in [429, 500, 502, 503, 504]:
                # レート制限、サーバーエラー、ゲートウェイエラー、サービス利用不可、タイムアウトの場合はリトライ
                retry_count += 1
                error_text = ""
                
                try:
                    # エラーの種類を確認
                    error_text = response.content.decode('utf-8', errors='replace')
                    
                    # 過負荷エラーを特別に処理
                    if "overloaded_error" in error_text or response.status_code == 429:
                        # トークン使用量制限の確認
                        if "quota" in error_text.lower() or "limit" in error_text.lower() or "usage" in error_text.lower() or "exceed" in error_text.lower():
                            return {
                                "success": False,
                                "error": "日次トークン使用量の上限に達しました。明日以降に再度お試しください。",
                                "details": error_text
                            }
                        # 過負荷エラーの場合
                        if retry_count >= max_retries:
                            return {
                                "success": False,
                                "error": "AIサーバーが混雑しています。しばらく時間をおいて再度お試しください。",
                                "details": error_text
                            }
                        # リトライ前により長く待機（レート制限の場合は特に重要）
                        continue
                except:
                    pass
                
                if retry_count >= max_retries:
                    # すべてのリトライを使い果たした場合
                    status_messages = {
                        429: "リクエスト数制限を超えました。しばらく時間をおいて再度お試しください。",
                        500: "サーバー内部エラーが発生しました。",
                        502: "ゲートウェイエラーが発生しました。",
                        503: "サービスが一時的に利用できません。",
                        504: "ゲートウェイタイムアウトが発生しました。"
                    }
                    error_message = status_messages.get(response.status_code, f"エラーが発生しました。ステータスコード: {response.status_code}")
                    
                    # エラーテキストからトークン制限を検出
                    if error_text and ("quota" in error_text.lower() or "limit" in error_text.lower() or "usage" in error_text.lower() or "exceed" in error_text.lower()):
                        error_message = "日次トークン使用量の上限に達しました。明日以降に再度お試しください。"
                    
                    return {
                        "success": False,
                        "error": error_message,
                        "details": error_text
                    }
            else:
                # その他のエラーコードは即座に返す（リトライしない）
                error_text = ""
                try:
                    error_text = response.content.decode('utf-8', errors='replace')
                    
                    # JSONとしてパースしてエラーメッセージを抽出
                    try:
                        error_json = json.loads(error_text)
                        # Anthropicのオーバーロードエラーを特別に処理
                        if "overloaded_error" in error_text:
                            return {
                                "success": False,
                                "error": "AIサーバーが現在混雑しています。しばらく時間をおいて再度お試しください。",
                                "details": error_text
                            }
                    except:
                        pass
                except:
                    error_text = "レスポンスの文字列化に失敗しました"
                    
                return {
                    "success": False,
                    "error": f"エラーが発生しました。ステータスコード: {response.status_code}",
                    "details": error_text
                }
        except requests.exceptions.Timeout:
            retry_count += 1
            if retry_count < max_retries:
                # 指数バックオフ - リトライ回数に応じて待機時間を増加
                wait_time = 2 ** retry_count
                time.sleep(wait_time)
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
                
                # <think>タグを削除して回答を表示
                answer = response["answer"]
                cleaned_answer = remove_think_tags(answer)
                message_placeholder.markdown(cleaned_answer)
                st.session_state.messages.append({"role": "assistant", "content": cleaned_answer})
            else:
                # エラーメッセージを表示
                error_msg = response.get('error', 'エラーが発生しました')
                details = str(response.get("details", ""))
                
                # JSONエラーを解析して読みやすくする
                if details and (details.startswith("{") or details.startswith("{")):
                    try:
                        # JSONエラーメッセージを解析
                        if isinstance(details, str):
                            # エスケープされたJSONの処理
                            if "\\\"" in details:
                                details = details.replace("\\\"", "\"").replace("\\\\", "\\")
                            
                            # JSONが重複してエスケープされているケースの処理
                            while "\\\"" in details:
                                details = details.replace("\\\"", "\"")
                            
                            # APIエラーの特定パターンを検出
                            if "invalid_param" in details and "run failed" in details.lower():
                                # これは典型的なDify経由のAPI呼び出しエラー
                                if "quota" in details.lower() or "limit" in details.lower() or "exceed" in details.lower() or "usage" in details.lower():
                                    error_msg = "日次トークン使用量の上限に達しました。明日以降に再度お試しください。"
                            
                            try:
                                error_data = json.loads(details)
                                
                                # Anthropicのオーバーロードエラーかチェック
                                if isinstance(error_data, dict):
                                    message = error_data.get("message", "")
                                    if isinstance(message, str) and "overloaded" in message.lower():
                                        error_msg = "AIサーバーが現在混雑しています。しばらく時間をおいて再度お試しください。"
                                    # トークン使用量の制限チェック
                                    elif "quota" in message.lower() or "limit" in message.lower() or "usage" in message.lower():
                                        error_msg = "日次トークン使用量の上限に達しました。明日以降に再度お試しください。"
                                    
                                    # code属性もチェック
                                    code = error_data.get("code", "")
                                    if code == "invalid_param" and "run failed" in message.lower():
                                        # トークンやリクエスト量の制限に関するキーワード
                                        if "quota" in message.lower() or "limit" in message.lower() or "exceed" in message.lower() or "usage" in message.lower():
                                            error_msg = "日次トークン使用量の上限に達しました。明日以降に再度お試しください。"
                            except:
                                # さらに複雑なネストされたJSONの抽出を試みる
                                import re
                                overloaded_match = re.search(r"overloaded_error", details, re.IGNORECASE)
                                if overloaded_match:
                                    error_msg = "AIサーバーが現在混雑しています。しばらく時間をおいて再度お試しください。"
                                # トークン使用量の制限を正規表現で検出
                                quota_match = re.search(r"(quota|limit|usage|exceed|token|日次)", details, re.IGNORECASE)
                                if quota_match:
                                    error_msg = "日次トークン使用量の上限に達しました。明日以降に再度お試しください。"
                    except Exception as e:
                        pass
                
                # よく発生するエラーに対する親切なメッセージ
                if "overloaded" in error_msg.lower() or "overloaded_error" in details.lower():
                    user_friendly_msg = "⚠️ AIサーバーが現在混雑しています。しばらく時間をおいて再度お試しください。"
                elif "quota" in error_msg.lower() or "limit" in error_msg.lower() or "usage" in error_msg.lower() or "exceed" in error_msg.lower() or "日次" in error_msg.lower():
                    user_friendly_msg = "⚠️ 日次トークン使用量の上限に達しました。明日以降に再度お試しください。"
                elif "timeout" in error_msg.lower():
                    user_friendly_msg = "⚠️ リクエストがタイムアウトしました。サーバーが混雑しているか、質問が複雑すぎる可能性があります。"
                elif "rate limit" in error_msg.lower():
                    user_friendly_msg = "⚠️ 短時間に多くのリクエストが送信されました。少し時間をおいてから再度お試しください。"
                else:
                    user_friendly_msg = f"⚠️ {error_msg}"
                
                message_placeholder.markdown(user_friendly_msg)
                
                # 詳細エラー情報を表示（開発者向け）
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
st.markdown("© 2025 戦国寝技拳法AI師範@Silent柔術 | Powered by Streamlit & Dify") 