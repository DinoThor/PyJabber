// import logo from './logo.svg';
// import './App.css';
import 'rsuite/dist/rsuite.min.css';
import SideBar from './components/sidebar/sidebar';
import { Outlet } from 'react-router-dom';
import Contact from './routes/userList/userList';


function App() {
  return (
    <div style={{
      display: "flex",
      flexDirection: "row",
      height: "100vh"
    }}>
      <SideBar/>
      <div style={{
        flex: 1,
        padding: 30,
        borderRadius: 2,
        borderWidth: 2,
        borderColor: "red"
      }}>
        <Outlet/>
      </div>
    </div>
  );
}

export default App;
