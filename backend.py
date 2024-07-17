# import os
from flask import Flask, request, jsonify,render_template
from datetime import datetime
from flask_cors import CORS
import pandas as pd
import requests
import json
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

port = 5000
app.config['PORT'] = port


def clean_json_string(s):
    # Remove any leading/trailing whitespace
    s = s.strip()
    
    # Ensure the string starts and ends with curly braces
    if not s.startswith('{'): s = '{' + s
    if not s.endswith('}'): s = s + '}'
    
    # Replace single quotes with double quotes
    s = s.replace("'", '"')
    
    # Ensure all keys are enclosed in double quotes
    s = re.sub(r'(\w+)(?=\s*:)', r'"\1"', s)
    
    return s

def get_question_keys(question,api_key):
    response = requests.post(
        "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": r"Get the date before which all OpenAI models should be checked. Then get the name and creation date of model worth 4 points. Then get the index and name of model on point 2, finally get the names of both models and a number present in point 1. Example -- {check:'12 May 2020',four_point:{model: 'gpt-3.5-io', created: '2021-05-15'},two_point:{model:'gpt-4o',index: 3}, one_point:{model1: 'gpt-6.4-turbo', model2: 'gpt-4.2-io', number: 12}} as json"},
                {"role": "user", "content": f"{question}"}
            ]
        }
    )
    result = response.json()
    content = result['choices'][0]['message']['content']
    try:
        # First, try to parse the content as-is
        return json.loads(content)
    except json.JSONDecodeError:
        # If that fails, try to clean up the content and parse again
        cleaned_content = clean_json_string(content)
        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            # If it still fails, print the cleaned content and raise the error
            print("Cleaned content that failed to parse:")
            print(cleaned_content)
            raise e 


@app.route('/ask', methods=['POST'])
def ask_question():
      
    data = request.json
    question = data.get('question')
    api_key = data.get('apiKey')
    URL = 'https://aiproxy.sanand.workers.dev/openai/v1/models'

    if not question:
        return jsonify({"error": "No question provided"}), 400

    if not api_key:
        return jsonify({"error": "No openai api key provided"}), 400

    try:
        r = requests.get(f"{URL}", headers={
        "Authorization": f"Bearer {api_key}"})
        models=r.json()['data']


        ques=get_question_keys(question,api_key)
        print(ques)
        print()
        date_check=datetime.strptime(ques['check'],'%d %B %Y').timestamp()
        filtered_models=sorted(list(filter(lambda model: model['created']<date_check,models)),
        key=lambda x:x['created'],reverse=True)

        sum=0
        for model in filtered_models:
            model['created'] = datetime.utcfromtimestamp(model['created']).strftime('%d-%m-%Y')

        data=pd.DataFrame(filtered_models)
        
        try:
            sum = sum+4 if (data[data['id']==ques['four_point']['model']]['created']==datetime.strptime(ques['four_point']['created'],'%Y-%m-%d').strftime('%d-%m-%Y')).to_list()[0] else sum
        except:
            sum=0
        try:
            index=ques['two_point']['index']
            sum=sum+2 if data.iloc[index,0]==ques['two_point']['model'] else sum
        except:
            sum=sum
        try:
            index=data[data['id']==ques['one_point']['model2']].index[0]+ques['one_point']['number']+1
            sum=sum+1 if data.iloc[index,0]==ques['one_point']['model1'] else sum
        except:
            sum=sum
        return jsonify({"answer":sum})
    except Exception as e:
        print('We are in error')
        print(str(e))
        return jsonify({"error":"Please check your question"}), 500

if __name__ == '__main__':
    # Print app specifications
    print("Flask App Specifications:")
    print(f"Host: {app.config.get('SERVER_NAME', 'Default: 0.0.0.0')}")
    print(f"Application root: {app.config.get('APPLICATION_ROOT', '/')}")
    
    # Run the app
    app.run()
