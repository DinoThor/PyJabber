import 'rsuite/dist/rsuite.min.css';
import SideBar from './components/sidebar/sidebar';
import { Outlet } from 'react-router-dom';


function App() {
  return (
    <div style={{height: "100vh"}}>
      <div style={{
        display: "flex",
        flex: 1,
        flexDirection: "row",
        alignItems: "stretch",
        height: "100%"
      }}>
        <SideBar />
        <div style={{
          flex: 1,
          padding: 30,
          borderRadius: 2,
          borderWidth: 2,
          borderColor: "red"
        }}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}

export default App;
