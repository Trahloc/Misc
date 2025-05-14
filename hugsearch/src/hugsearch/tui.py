"""
# PURPOSE: Provides the Terminal User Interface for hugsearch using Textual

## INTERFACES:
- HugSearchApp: Main application class
- SearchInput: Search input widget with as-you-type functionality
- ResultsList: Scrollable results view with mouse support
- StatusBar: Shows update status and search info

## DEPENDENCIES:
- textual: TUI framework
- rich: Text formatting
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Input, ListView, Footer, Header
from textual.screen import Screen
from textual.binding import Binding
from textual.message import Message


class SearchInput(Input):
    """
    PURPOSE: Search input with real-time search capabilities
    """

    class SearchChanged(Message):
        def __init__(self, query: str) -> None:
            self.query = query
            super().__init__()

    def on_input_changed(self) -> None:
        """Emit search changed event for real-time search"""
        self.post_message(self.SearchChanged(self.value))


class ResultsList(ListView):
    """
    PURPOSE: Display search results with mouse interaction
    """

    def on_list_view_selected(self, selected: ListView.Selected) -> None:
        """Handle result selection"""
        self.post_message(self.Selected(selected.item))


class StatusBar(Footer):
    """
    PURPOSE: Show status updates and search information
    """

    def __init__(self) -> None:
        super().__init__()
        self.update_status("Ready")

    def update_status(self, message: str) -> None:
        """Update status message"""
        self.highlight_key = message


class SearchScreen(Screen):
    """
    PURPOSE: Main search interface screen
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+r", "refresh", "Refresh", show=True),
        Binding("ctrl+f", "focus_search", "Search", show=True),
        Binding("ctrl+h", "toggle_help", "Help", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            SearchInput(placeholder="Search models... (AND/OR supported)"),
            Vertical(ResultsList(), id="results_container"),
            StatusBar(),
        )

    async def on_search_input_search_changed(
        self, message: SearchInput.SearchChanged
    ) -> None:
        """
        Handle real-time search updates
        """
        # Update results list based on search
        await self.update_results(message.query)

    async def update_results(self, query: str) -> None:
        """
        Update results based on search query
        """
        # TODO: Implement actual search using database.search_models
        pass

    async def action_refresh(self) -> None:
        """
        Handle manual refresh action
        """
        # TODO: Implement refresh using scheduler.refresh_models
        pass


class HugSearchApp(App):
    """
    PURPOSE: Main application class
    """

    TITLE = "HugSearch"
    SUB_TITLE = "Local Hugging Face Model Search"
    CSS = """
    SearchInput {
        dock: top;
        margin: 1 1;
        border: heavy $accent;
    }

    ResultsList {
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }

    StatusBar {
        background: $accent;
        color: $text;
        height: 1;
    }
    """

    def on_mount(self) -> None:
        """
        Initialize application
        """
        self.push_screen(SearchScreen())
