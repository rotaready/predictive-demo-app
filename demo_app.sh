# open chatbot in background then run flask
cd "/Users/barry.walsh/rotaready/rr_repos/predictive-demo-app/apps/genai-vite/ldfe-genai-demo" 
npm run dev & 
cd "/Users/barry.walsh/rotaready/rr_repos/predictive-demo-app" 
flask run -h localhost -p 5002
