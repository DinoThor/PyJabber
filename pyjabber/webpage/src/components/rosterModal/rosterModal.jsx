import { useState, useEffect } from "react";
import { Button, Modal } from "rsuite";
import { List } from 'rsuite';


export default function RosterModal({ rosterVisible, rosterSelected, setRosterSelected, setRosterVisible }) {

  const [roster, setRoster] = useState([])

  function retriveRoster() {
    if (rosterSelected > -1) {
      fetch(`http://localhost:9090/api/roster/${rosterSelected}`, { method: 'GET' })
        .then((res) => {
          if (!res.ok) {
            throw new Error('Network response was not ok');
          }
          return res.json();
        })
        .then((data) => {
          setRoster(data)
        });
    }

  }

  useEffect(() => {
    retriveRoster()
  }, [rosterSelected]);

  return (
    <Modal
      open={rosterVisible}
      onClose={setRosterVisible}
    >
      <Modal.Header>
        <Modal.Title>Roster</Modal.Title>
      </Modal.Header>
      <Modal.Body>

        <List bordered style={{margin: 10}}>
          {roster.map(item => (
            <List.Item>{item["item"]}</List.Item>
          ))}
        </List>

      </Modal.Body>
      <Modal.Footer>
        <Button onClick={() => {
          setRosterSelected(-1)
          setRosterVisible(false)
        }} >
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  )
}