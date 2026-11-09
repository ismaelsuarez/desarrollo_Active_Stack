import { Button, Notice, TextField } from '../components/ui';

type Props = {
  services: { id: number; nombre: string; duracion_min: number }[];
  professionals: { id: number; nombre: string }[];
  service: string;
  professional: string;
  date: string;
  busy: boolean;
  searching: boolean;
  onServiceChange: (value: string) => void;
  onProfessionalChange: (value: string) => void;
  onDateChange: (value: string) => void;
  onSearch: () => void;
};

export function BookingForm({ services, professionals, service, professional, date, busy, searching,
  onServiceChange, onProfessionalChange, onDateChange, onSearch }: Props) {
  return <div className="public-card booking-card"><h2>Elegí qué necesitás</h2><div className="public-form booking-form">
    <label>Prestación<select disabled={busy} value={service} onChange={event => onServiceChange(event.target.value)}><option value="">Elegí una prestación</option>{services.map(item => <option key={item.id} value={item.id}>{item.nombre} · {item.duracion_min} min</option>)}</select></label>
    <label>Profesional<select disabled={busy} value={professional} onChange={event => onProfessionalChange(event.target.value)}><option value="">Elegí un profesional</option>{professionals.map(item => <option key={item.id} value={item.id}>{item.nombre}</option>)}</select></label>
    <TextField label="Fecha" type="date" disabled={busy} value={date} onChange={event => onDateChange(event.target.value)} />
    {searching && <Notice>Buscando horarios…</Notice>}
    <Button variant="secondary" disabled={busy || searching || !service || !professional || !date} onClick={onSearch}>Buscar horarios</Button>
  </div></div>;
}
