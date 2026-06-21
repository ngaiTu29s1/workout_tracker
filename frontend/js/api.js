// API Fetch Wrapper

const API_BASE = '/api';

function getApiKey() {
  let key = localStorage.getItem('FITNESS_OS_API_KEY');
  if (!key) {
    key = prompt('Please enter your API Key to access Fitness OS:');
    if (key) {
      localStorage.setItem('FITNESS_OS_API_KEY', key);
    }
  }
  return key || '';
}

async function handleResponse(res) {
  if (res.status === 401) {
    localStorage.removeItem('FITNESS_OS_API_KEY');
    window.location.reload();
    throw new Error('Unauthorized');
  }
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
    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        'X-API-Key': getApiKey()
      }
    });
    return handleResponse(res);
  },

  async post(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': getApiKey()
      },
      body: JSON.stringify(body)
    });
    return handleResponse(res);
  },

  async put(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': getApiKey()
      },
      body: JSON.stringify(body)
    });
    return handleResponse(res);
  },

  async delete(path) {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'DELETE',
      headers: {
        'X-API-Key': getApiKey()
      }
    });
    return handleResponse(res);
  }
};
