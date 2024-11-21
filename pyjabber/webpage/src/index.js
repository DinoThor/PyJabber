import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import ErrorPage from './routes/error-pages';
import Contact from './routes/userList/userList';
import Settings from './routes/settings/settings';
import Dashboard from './routes/dashboard/dashboard';

const root = createRoot(document.getElementById('root'));

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    errorElement: <ErrorPage />,
    children: [
      {
        path: "/",
        element: <Dashboard />,
      },
      {
        path: "users/",
        element: <Contact />,
      },
      {
        path: "settings/",
        element: <Settings />,
      },
    ]
  },
   
]);

root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
