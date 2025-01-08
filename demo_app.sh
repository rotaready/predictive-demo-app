# kill all running python processes - use sudo if need admin password 
killall Python .

#close down problem open ports (5173 I think is vite default, 5002 is flask but *check* dont close this down as causes ngrok to boot out ??)
# see https://stackoverflow.com/questions/38425334/close-many-ports-at-once
# problem potys below *refactor* to a list of ports
for i in {5170..5180}
do
   kill -kill `lsof -t -i tcp:$i`
done

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
flask run -h localhost -p 5002 &

sleep 5  # Waits 10 seconds for app to load

# 4. open chrome browser for app
open -a "Google Chrome" \
  --args --new-window https://90dc-212-54-135-152.ngrok-free.app/index &
