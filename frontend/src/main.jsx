import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';

// Punto de entrada: React dibuja la aplicación dentro del elemento root de index.html.
createRoot(document.getElementById('root')).render(<App />);
