"""Flask health check endpoint for monitoring."""

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    """Health check endpoint for monitoring and load balancers.

    Returns
    -------
        JSON response with status indicator

    """
    return jsonify(status="ok")
