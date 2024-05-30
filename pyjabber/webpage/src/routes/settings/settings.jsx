import { Toggle } from 'rsuite';

export default function Settings() {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      padding: 20
    }}>
      <Toggle style={{padding: 5}} />
      <Toggle style={{padding: 5}} defaultChecked />
      <Toggle style={{padding: 5}} defaultChecked />
      <Toggle style={{padding: 5}} defaultChecked />
      <Toggle style={{padding: 5}} />
    </div>
  )
}