import { Table, Button } from 'rsuite';
import { useEffect, useState } from 'react';
import TrashIcon from '@rsuite/icons/Trash';
import VisibleIcon from '@rsuite/icons/Visible';
import FormModal from '../../components/form/Form';
import RosterModal from '../../components/rosterModal/rosterModal';

const { Column, HeaderCell, Cell } = Table;

export default function Contact() {
  const [users, setUsers] = useState([]);
  const [rosterSelected, setRosterSelected] = useState(-1);
  const [rosterVisible, setRosterVisible] = useState(false);
  const [formVisible, setFormVisible] = useState(false);

  function retrieveUserList() {
    fetch('http://localhost:9090/api/users')
      .then((res) => {
        return res.json();
      })
      .then((data) => {
        setUsers(data);
      });
  }

  function handleDelete(id) {
    fetch(`http://localhost:9090/api/users/${id}`, {
      method: 'DELETE'
    }
    ).then(response => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
      .then(() => {
        retrieveUserList()
      })
      .catch(error => {
        console.error('Error:', error);
      });
  }

  useEffect(() => {
    retrieveUserList()
  }, []);

  useEffect(() => {
    retrieveUserList()
  }, [formVisible]);

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent:"center",
      height: "100%"
    }}>

      <FormModal formVisible={formVisible} setFormVisible={setFormVisible} />
      <RosterModal
        rosterVisible={rosterVisible}
        rosterSelected={rosterSelected}
        setRosterSelected={setRosterSelected}
        setRosterVisible={setRosterVisible}
      />

      <div
        style={{
          justifyContent: "flex-start",
          padding: 20,
          margin: 20,
          display: "flex",
          flexDirection: "column",
        }}>
        <Button color="green" appearance="primary" onClick={() => setFormVisible(true)} style={{width: 200}}>
          Crear usuario
        </Button>
      </div>
      <div>
        <Table
        data={users}
        style={{ flex: 1, width: 400, alignSelf: "center"}}
        fillHeight={true}
        bordered={true}
      >
        <Column align="center" fixed>
          <HeaderCell>Id</HeaderCell>
          <Cell dataKey="id" />
        </Column>
        <Column align="center" fixed>
          <HeaderCell>JID</HeaderCell>
          <Cell dataKey="jid" />
        </Column>
        <Column align="center">
          <HeaderCell >Roster</HeaderCell>
          <Cell style={{ padding: '6px' }}>
            {rowData => (
              <Button appearance="link" onClick={() => {
                setRosterSelected(rowData.id)
                setRosterVisible(true)
              }}>
                  <VisibleIcon style={{ fontSize: 15 }} />
              </Button>
            )}
          </Cell>
        </Column>
        <Column align="center">
          <HeaderCell />
          <Cell style={{ padding: '6px' }}>
            {rowData => (
              <Button appearance="link" onClick={() => {
                let a = window.confirm(`Are you sure to delete ID:${rowData.id}?`)
                if (a)
                  handleDelete(rowData.id)
              }}>
                <TrashIcon style={{
                  fontSize: 15,
                  color: "red"
                }} />
              </Button>
            )}
          </Cell>
        </Column>
      </Table>
      </div>
    </div>
  );
};
