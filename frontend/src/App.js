import React, { useState, useRef, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import './App.css';

// Helper to format the pulse
const getPulseInfo = (pulse) => {
  switch (pulse) {
    case 'bullish':
      return { color: '#28a745', icon: '▲' };
    case 'bearish':
      return { color: '#dc3545', icon: '▼' };
    default:
      return { color: '#6c757d', icon: '●' };
  }
};

function App() {
  const [ticker, setTicker] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ticker.trim() || isLoading) return;

    const userMessage = { sender: 'user', text: ticker };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setTicker('');

    try {
      const response = await fetch(`/api/v1/market-pulse?ticker=${ticker}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch data');
      }
      const data = await response.json();
      const botMessage = { sender: 'bot', data };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMessage = { sender: 'bot', text: `Error: ${error.message}` };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const BotMessage = ({ data }) => {
    const pulseInfo = getPulseInfo(data.pulse);
    const returnsData = data.momentum.returns.map((value, index) => ({ name: `Day ${index - 5}`, value }));

    return (
      <div className="bot-message-card">
        <div className="card-header">
          <h3>{data.ticker} Pulse: <span style={{ color: pulseInfo.color }}>{data.pulse.charAt(0).toUpperCase() + data.pulse.slice(1)} {pulseInfo.icon}</span></h3>
        </div>
        <p className="explanation">{data.llm_explanation}</p>
        
        <div className="card-section">
          <h4>Momentum</h4>
          <div className="momentum-details">
            <p><strong>Simple Score:</strong> {data.momentum.simple_score}</p>
            <p><strong>Advanced Score (vs 20-day SMA):</strong> {data.momentum.advanced_score !== null ? `${data.momentum.advanced_score}%` : 'N/A'}</p>
          </div>
          <div className="sparkline-container">
            <ResponsiveContainer width="100%" height={100}>
              <LineChart data={returnsData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={isDarkMode ? "#444" : "#ccc"} />
                <XAxis dataKey="name" stroke={isDarkMode ? "#888" : "#666"} />
                <YAxis stroke={isDarkMode ? "#888" : "#666"} />
                <Tooltip
                  contentStyle={{ backgroundColor: isDarkMode ? '#333' : '#fff', border: '1px solid #ccc' }}
                  labelStyle={{ color: isDarkMode ? '#fff' : '#000' }}
                />
                <Line type="monotone" dataKey="value" stroke="#8884d8" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card-section">
          <h4>Recent News</h4>
          <ul>
            {data.news.map((item, index) => (
              <li key={index}>
                <a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a>
                <span className="sentiment-score" style={{ color: item.sentiment > 0 ? '#28a745' : item.sentiment < 0 ? '#dc3545' : '#6c757d' }}>
                  ({item.sentiment.toFixed(2)})
                </span>
              </li>
            ))}
          </ul>
        </div>

        <details>
          <summary>Show Full JSON Response</summary>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </details>
      </div>
    );
  };

  return (
    <div className={`App ${isDarkMode ? 'dark-mode' : 'light-mode'}`}>
      <header className="App-header">
        <h1>Market-Pulse</h1>
        <button onClick={() => setIsDarkMode(!isDarkMode)} className="theme-toggle">
          {isDarkMode ? '☀️' : '🌙'}
        </button>
      </header>
      <div className="chat-container">
        <div className="message-list">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.sender}`}>
              {msg.sender === 'bot' ? (
                msg.data ? <BotMessage data={msg.data} /> : <div className="error-message">{msg.text}</div>
              ) : (
                <div className="user-message">{msg.text}</div>
              )}
            </div>
          ))}
          {isLoading && <div className="message bot"><div className="loading-indicator"><span>.</span><span>.</span><span>.</span></div></div>}
          <div ref={messagesEndRef} />
        </div>
        <form onSubmit={handleSubmit} className="message-form">
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="Enter a stock ticker (e.g., AAPL, NVDA)..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading}>
            {isLoading ? '...' : '➤'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
