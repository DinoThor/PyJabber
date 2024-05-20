import { Table, Button } from 'rsuite';
import { useEffect, useState } from 'react';
import TrashIcon from '@rsuite/icons/Trash';
import FormModal from '../../components/form/Form';

const { Column, HeaderCell, Cell } = Table;


export default function Contact() {
  const [users, setUsers] = useState([]);
  const [formVisible, setFormVisible] = useState(false);

  function retriveUserList() {
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
        retriveUserList()
      })
      .catch(error => {
        console.error('Error:', error); 
      });
  }

  useEffect(() => {
    retriveUserList()
  }, []);

  useEffect(() => {
    retriveUserList()
  }, [formVisible]);

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent:"center",
      height: "100%"
    }}>

      <FormModal formVisible={formVisible} setFormVisible={setFormVisible} retriveUserList={retriveUserList}/>
      
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
        style={{ flex: 1, width: 300, alignSelf: "center"}}
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
          <HeaderCell />
          <Cell style={{ padding: '6px' }}>
            {rowData => (
              <Button appearance="link" onClick={() => {
                let a = window.confirm(`¿Estas seguro de eliminar ID:${rowData.id}?`)
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
