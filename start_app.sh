while ! curl http://localhost:5002 -m1 -o/dev/null -s ; do
  sleep 0.1
  echo "Flask app still loading" #This line is for testing purposes
done
sudo python startup.py
echo "Startup complete. Appp Ready!"
