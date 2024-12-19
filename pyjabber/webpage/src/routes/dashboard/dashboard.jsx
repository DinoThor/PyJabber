import {useState, useEffect} from 'react';
import { Panel } from 'rsuite';
import { io } from 'socket.io-client';


export default function Dashboard() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const socket = io('http://localhost:9090/ws');

    socket.on('log', (data) => {
      setLogs((prevLogs) => [...prevLogs, data.message]);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      padding: 20
    }}>
      <Panel
        header="Log"
        style={{ padding: 30, height: '50vh' }}
        bordered
        bodyFill
      >
        <div style={{ padding: 10, backgroundColor: '#EEE', borderRadius: 10, overflow: 'scroll'}}>
        {logs.map((log, index) => (
          <li key={index}>{log}</li>
        ))}
        </div>
      </Panel>
    </div>
  )
}
