import axios from 'axios';

const API_BASE = 'http://localhost:8888';

export const getAlerts = async () => {
  try {
    const response = await axios.get(`${API_BASE}/alerts`);
    return response.data;
  } catch (error) {
    console.error("Error fetching alerts:", error);
    return { active_threats: [] };
  }
};

export const postIntelligence = async (query) => {
  try {
    const response = await axios.post(`${API_BASE}/intelligence`, { query });
    return response.data;
  } catch (error) {
    console.error("Error querying JARVIS:", error);
    return { synthesis: "Error: Could not reach the Sovereign Inference Engine." };
  }
};
