import { Sidenav, Nav } from 'rsuite';
import DashboardIcon from '@rsuite/icons/legacy/Dashboard';
import GroupIcon from '@rsuite/icons/legacy/Group';
import MagicIcon from '@rsuite/icons/legacy/Magic';
import GearCircleIcon from '@rsuite/icons/legacy/GearCircle';
import { Link } from 'react-router-dom';
import { useNavigate } from "react-router-dom";


export default function SideBar() {
  const navigate = useNavigate();
  
  return (
    <div style={{ width: 240 }}>
      <Sidenav defaultOpenKeys={['3', '4']} appearance='subtle' >
        <Sidenav.Body>
          <Nav activeKey="1">
            <Nav.Item eventKey="1" icon={<DashboardIcon />} onClick={() => navigate("/")}>
              Control Panel
            </Nav.Item>

            <Nav.Item eventKey="2" icon={<GroupIcon />} onClick={() => navigate("/users")}>
                Users
            </Nav.Item>

            <Nav.Menu eventKey="4" title="Settings" icon={<GearCircleIcon />}>
              <Nav.Item eventKey="4-1">Applications</Nav.Item>
              <Nav.Item eventKey="4-2">Channels</Nav.Item>
              <Nav.Item eventKey="4-3">Versions</Nav.Item>
            </Nav.Menu>
          </Nav>
        </Sidenav.Body>
      </Sidenav>
    </div>
  )
};