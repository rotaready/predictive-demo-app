# 1. NLP to SQL
# open chatbot in background and chainlit multi-modal UI with audio support then run flask
cd "/Users/barry.walsh/rotaready/rr_repos/predictive-demo-app/apps/genai-vite/ldfe-genai-demo" 
npm run dev & 

# 2. Azure OpenAI GPT 4o with chainlit audio support
# old: cd "/Users/barry.walsh/rotaready/rr_repos/predictive-demo-app/apps/genai/audio"
# chainlit run chainlit_audio_assistant.py -w -h &
cd "/Users/barry.walsh/rotaready/rr_repos/predictive-demo-app/apps/genai/chainlit"
chainlit run app.py -w -h &

# 3. run this app
cd "/Users/barry.walsh/rotaready/rr_repos/predictive-demo-app" 
flask run -h localhost -p 5002
