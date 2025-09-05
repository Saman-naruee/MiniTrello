document.addEventListener('alpine:init', () => {
    Alpine.data('boardApp', () => ({
        addCardToList(listId, boardId) {
            // Use HTMX to load the create card form
            // The URL should be correct as per our urls.py
            htmx.ajax('GET', `/boards/${boardId}/lists/${listId}/cards/create/`, {
                target: `#cards-container-${listId}`,
                swap: 'beforeend',
                // We might need to adjust this swap strategy if we want to replace a 'add card' button with the form
                // For now, it will append the form.
            });
        },

        editCard(cardId, listId, boardId) {
            // Use HTMX to load the edit card form
            htmx.ajax('GET', `/boards/${boardId}/lists/${listId}/cards/${cardId}/update/`, {
                target: `#card-${cardId}`,
                swap: 'outerHTML',
            });
        },

        confirmDelete(cardId, listId, boardId) {
            if (confirm("Are you sure you want to delete this card?")) {
                htmx.ajax('DELETE', `/boards/${boardId}/lists/${listId}/cards/${cardId}/delete/`, {
                    target: `#card-${cardId}`,
                    swap: 'outerHTML',
                });
            }
        }
    }));
});
