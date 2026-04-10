// SupportFlow/screens/WelcomeMessageScreen.jsx
import Button from "../../Button/Button";
import ButtonFrame from "../../Button/ButtonFrame";

function getWelcomeMessage(loginState, loginStreak) {
  switch (loginState) {
    case "first_login_ever":
      return "Welcome! This is your first login, starting your streak.";
    case "already_logged_today":
      return `Welcome back! You logged in earlier today. Your login streak is ${loginStreak} days.`;
    case "streak_continues":
      return `Welcome back! Your login streak is now ${loginStreak} days.`;
    case "streak_reset":
      return "Welcome back, we missed you! Your login streak has been reset.";
    default:
      return "Welcome back! You showed up today.";
  }
}

export default function WelcomeMessageScreen({ loginState, loginStreak, onStart, onSupport }) {
  const message = getWelcomeMessage(loginState, loginStreak);

  return (
    <div>
      <p>{message}</p>
      <ButtonFrame>
        <Button onClick={onStart}>Start</Button>
        <Button onClick={onSupport}>Get support</Button>
      </ButtonFrame>
    </div>
  );
}
