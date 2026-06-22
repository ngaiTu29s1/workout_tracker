// API Fetch Wrapper

const API_BASE = '/api';

async function handleResponse(res) {
  if (!res.ok) {
    let errorDetail = 'An error occurred';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch (e) {
      try {
        errorDetail = await res.text() || errorDetail;
      } catch (textErr) {}
    }
    throw new Error(errorDetail);
  }
  
  try {
    const json = await res.json();
    return json; // Envelope contains { data, message, status }
  } catch (e) {
    return { data: null, message: 'Success', status: 'ok' };
  }
}

export const api = {
  async get(path) {
    const res = await fetch(`${API_BASE}${path}`);
    return handleResponse(res);
  },

  async post(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    return handleResponse(res);
  },

  async put(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    return handleResponse(res);
  },

  async delete(path) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'DELETE'
    });
    return handleResponse(res);
  }
};
