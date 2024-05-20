import { Toggle } from 'rsuite';
import { Panel, Placeholder } from 'rsuite';


export default function Dashboard() {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      padding: 20
    }}>
      <Panel
        header="Stats"
        style={{ marginBottom: 30 }}
        bordered>
        <Placeholder.Paragraph />
      </Panel>
      <Panel
        header="Stats"
        style={{ marginBottom: 30 }}
        bordered>
        <Placeholder.Paragraph />
      </Panel>
      <Panel
        header="Stats"
        style={{ marginBottom: 30 }}
        bordered>
        <Placeholder.Paragraph />
      </Panel>
    </div>
  )
}