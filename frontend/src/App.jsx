import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import ProtectedLayout from "./components/ProtectedLayout";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";
import MovieDetailPage from "./pages/MovieDetailPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import ChatPage from "./pages/ChatPage";

// App-wide routing. Public routes (login/register) sit at the top level;
// everything else is nested under <ProtectedLayout>, which redirects to
// /login when there's no JWT and renders the shared navbar otherwise.
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected (require a JWT) */}
        <Route element={<ProtectedLayout />}>
          <Route path="/home" element={<HomePage />} />
          <Route path="/movie/:id" element={<MovieDetailPage />} />
          <Route path="/recommendations" element={<RecommendationsPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Route>

        {/* Defaults */}
        <Route path="/" element={<Navigate to="/home" replace />} />
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
