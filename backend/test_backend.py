# Teste simples do backend
import json
from urllib import request
import urllib.error

BASE = 'http://localhost:5000'


def get(path):
    try:
        res = request.urlopen(BASE + path)
        return res.read().decode('utf-8')
    except urllib.error.URLError as e:
        print('Erro ao acessar', path, e)
        return None


def post_json(path, payload):
    req = request.Request(BASE + path, method='POST')
    req.add_header('Content-Type', 'application/json')
    data = json.dumps(payload).encode('utf-8')
    try:
        res = request.urlopen(req, data=data)
        return json.loads(res.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print('Erro POST', path, e)
        return None


if __name__ == '__main__':
    print('Health:', get('/health'))
    gen = post_json('/exams/generate', {'student_id': 'test', 'date': '2026-06-10'})
    print('Generate response:', gen)
    key = post_json('/exams/answer_key', {'student_id': 'test', 'date': '2026-06-10'})
    print('Answer key response:', key)
