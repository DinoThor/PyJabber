import { Sidenav, Nav } from 'rsuite';
import DashboardIcon from '@rsuite/icons/legacy/Dashboard';
import GroupIcon from '@rsuite/icons/legacy/Group';
import GearCircleIcon from '@rsuite/icons/legacy/GearCircle';
import { useNavigate } from "react-router-dom";
import { useState } from 'react';


export default function SideBar() {
  const navigate = useNavigate();
  const [activate, setActivate] = useState(1);

  return (
    <div style={{ width: 240 }}>
      <Sidenav appearance='inverse' style={{ height: "100%" }}>
        <Sidenav.Header>
          <div style={{ padding: 20, fontSize: 16, }}>
            PyJabber
          </div>
        </Sidenav.Header>
        <Sidenav.Body>
          <Nav activeKey={activate.toString()}>
            <Nav.Item eventKey="1" icon={<DashboardIcon />} onClick={() => { setActivate(1); navigate("/") }}>
              Control Panel
            </Nav.Item>

            <Nav.Item eventKey="2" icon={<GroupIcon />} onClick={() => { setActivate(2); navigate("/users") }}>
              Users
            </Nav.Item>

            <Nav.Item eventKey="3" icon={<GearCircleIcon />} onClick={() => { setActivate(3); navigate("/settings")}}>
              Settings
            </Nav.Item>
          </Nav>
        </Sidenav.Body>
      </Sidenav>
    </div>
  )
};