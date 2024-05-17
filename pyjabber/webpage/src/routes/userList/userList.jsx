import { Table, Button } from 'rsuite';
import { useState, useEffect } from 'react';
import TrashIcon from '@rsuite/icons/Trash';

const { Column, HeaderCell, Cell } = Table;

const mockData = [
  {
    "id": 1,
    "jid": "demo",
    "hash": 13213213
  }, {
    "id": 2,
    "jid": "test",
    "hash": 13213213
  }, {
    "id": 3,
    "jid": "miguel",
    "hash": 13213213
  }, {
    "id": 4,
    "jid": "agent1",
    "hash": 13213213
  }, {
    "id": 5,
    "jid": "demo",
    "hash": 13213213
  }, {
    "id": 6,
    "jid": "demo",
    "hash": 13213213
  }
]

export default function Contact() {
  const [users, setUsers] = useState([]);


  // useEffect(() => {
  //   console.log("JASDASHD")
  //   fetch('http://localhost:9090/api/users')
  //     .then((res) => {
  //       return res.json();
  //     })
  //     .then((data) => {
  //       console.log(data);
  //       setUsers(data);
  //     });
  // }, []);

  return (
    <Table height={500}
          data={mockData}
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
              console.log(a)
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
  );
};



