import { Table, Button } from 'rsuite';

const { Column, HeaderCell, Cell } = Table;

const mockData = [
  {
    "id": 1,
    "jid": "demo",
    "hash": 13213213
  }, {
    "id": 1,
    "jid": "demo",
    "hash": 13213213
  }, {
    "id": 1,
    "jid": "demo",
    "hash": 13213213
  }, {
    "id": 1,
    "jid": "demo",
    "hash": 13213213
  }, {
    "id": 1,
    "jid": "demo",
    "hash": 13213213
  }, {
    "id": 1,
    "jid": "demo",
    "hash": 13213213
  }
]

export default function Contact() {
  return (
    <Table
      height={400}
      data={mockData}
      onRowClick={rowData => {
        console.log(rowData);
      }}
    >
      <Column width={60} align="center" fixed>
        <HeaderCell>Id</HeaderCell>
        <Cell dataKey="id" />
      </Column>

      <Column width={150}>
        <HeaderCell>First Name</HeaderCell>
        <Cell dataKey="jid" />
      </Column>

      <Column width={150}>
        <HeaderCell>Last Name</HeaderCell>
        <Cell dataKey="hash" />
      </Column>
      {/* 
      <Column width={100}>
        <HeaderCell>Gender</HeaderCell>
        <Cell dataKey="gender" />
      </Column>

      <Column width={100}>
        <HeaderCell>Age</HeaderCell>
        <Cell dataKey="age" />
      </Column>

      <Column width={150}>
        <HeaderCell>Postcode</HeaderCell>
        <Cell dataKey="postcode" />
      </Column>

      <Column width={300}>
        <HeaderCell>Email</HeaderCell>
        <Cell dataKey="email" />
      </Column> */}
      {/* <Column width={80} fixed="right">
        <HeaderCell>...</HeaderCell>

        <Cell style={{ padding: '6px' }}>
          {rowData => (
            <Button appearance="link" onClick={() => alert(`id:${rowData.id}`)}>
              Edit
            </Button>
          )}
        </Cell>
      </Column> */}
    </Table>
  );
};



