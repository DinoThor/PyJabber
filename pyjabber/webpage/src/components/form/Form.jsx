import { useState } from "react";
import { Button, Input, InputGroup, Modal } from "rsuite";
import EyeIcon from '@rsuite/icons/legacy/Eye';
import EyeSlashIcon from '@rsuite/icons/legacy/EyeSlash';


export default function FormModal({formVisible, setFormVisible}) {
  const [visible, setVisible] = useState(false);
  const [jid, setJid] = useState("");
  const [pwd, setPwd] = useState("");

  function handleRegister() {
    let data = {
      jid: jid,
      pwd: pwd
    }

    fetch('http://localhost:9090/api/createuser',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      }
    )
      .then((res) => {
        if (!res.ok) {
          throw new Error('Network response was not ok');
        }
        return res.json();
      })
      .then((data) => {
      });
  }


  return (
    <Modal
      open={formVisible}
      onClose={setFormVisible}
    >
      <Modal.Header>
        <Modal.Title>Create user</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Input placeholder="JID" style={{ marginBottom: 10 }} onChange={(value) => setJid(value)}/>
        <InputGroup inside>
          <Input type={visible ? 'text' : 'password'} onChange={(value) => setPwd(value)}/>
          <InputGroup.Button onClick={() => {setVisible(!visible)}}
          >
            {visible ? <EyeIcon /> : <EyeSlashIcon />}
          </InputGroup.Button>
        </InputGroup>
      </Modal.Body>
      <Modal.Footer>
        <Button onClick={() => {
          setFormVisible(false)
          handleRegister()
        }} appearance="primary">
          Ok
        </Button>
        <Button onClick={() => setFormVisible(false)} appearance="subtle">
          Cancel
        </Button>
      </Modal.Footer>
    </Modal>
  )
}