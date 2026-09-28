from unittest.mock import patch

from main import main


def test_main_starts_user_interaction() -> None:
    """Application entry point should start the complete console workflow."""
    with patch("main.user_interaction") as interaction:
        main()

    interaction.assert_called_once_with()
