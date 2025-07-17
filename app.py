from flask import Flask, request, jsonify
from executor import SecurePythonExecutor

app = Flask(__name__)
executor = SecurePythonExecutor()

@app.route('/execute', methods=['POST'])
def execute_python():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        if not data or 'script' not in data:
            return jsonify({"error": "Missing 'script' field in request body"}), 400
        
        script = data['script']
        if not isinstance(script, str) or not script.strip():
            return jsonify({"error": "Script must be a non-empty string"}), 400
        
        result = executor.execute_script(script)
        
        if result.get("success"):
            return jsonify({
                "result": result["result"],
                "stdout": result["stdout"]
            })
        else:
            return jsonify({
                "error": result.get("error", "Unknown error"),
                "stdout": result.get("stdout", "")
            }), 400
            
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)