import React from 'react';
import { Dashboard } from './components/Dashboard';

function App() {
  const serverUrl = import.meta.env.VITE_SERVER_URL || 'http://localhost:3000';
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:3000';

  return (
    <div className="app">
      <Dashboard serverUrl={serverUrl} wsUrl={wsUrl} />
    </div>
  );
}

export default App;
