/**
 * VPSWeb Common JavaScript Functions
 * Centralized utility functions used across multiple pages
 */

// BBR Modal Global Variables
let currentBBR = null;
let isDragging = false;
let isResizing = false;
let dragOffset = { x: 0, y: 0 };
let initialSize = { width: 0, height: 0 };
let initialPos = { x: 0, y: 0 };
let currentResizeHandle = null;
let initialMousePos = { x: 0, y: 0 };

// Toast notification system
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toast = document.createElement('div');

    // Style based on type
    const baseClasses = 'px-4 py-3 rounded-lg shadow-lg transform transition-all duration-300 ease-in-out translate-x-full';
    let typeClasses = '';
    let icon = '';

    switch (type) {
        case 'success':
            typeClasses = 'bg-green-500 text-white';
            icon = `<svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>`;
            break;
        case 'error':
            typeClasses = 'bg-red-500 text-white';
            icon = `<svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>`;
            break;
        case 'warning':
            typeClasses = 'bg-yellow-500 text-white';
            icon = `<svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>`;
            break;
        default:
            typeClasses = 'bg-blue-500 text-white';
            icon = `<svg class="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>`;
    }

    toast.className = `${baseClasses} ${typeClasses}`;
    toast.innerHTML = `${icon}${message}`;

    // Add to container
    toastContainer.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.classList.remove('translate-x-full');
        toast.classList.add('translate-x-0');
    }, 10);

    // Remove after 5 seconds
    setTimeout(() => {
        toast.classList.remove('translate-x-0');
        toast.classList.add('translate-x-full');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 5000);
}

// Show error message (wrapper for showToast)
function showError(message) {
    showToast(message, 'error');
    console.error('Error:', message);
}

// Show success message (alias for showToast)
function showSuccessMessage(message) {
    showToast(message, 'success');
}

// Show notification (alias for showToast)
function showNotification(message, type = 'info') {
    showToast(message, type);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Initialize synchronized scrolling
function initializeSyncScroll() {
    // Make it layout-agnostic - find all sync-scroll elements in any layout
    const scrollableElements = document.querySelectorAll('.sync-scroll');
    if (scrollableElements.length === 0) return;

    let isSyncing = false;
    scrollableElements.forEach(element => {
        element.addEventListener('scroll', event => {
            if (isSyncing) return;
            isSyncing = true;
            const sourceElement = event.target;
            const scrollPercentage = sourceElement.scrollTop / (sourceElement.scrollHeight - sourceElement.clientHeight);

            scrollableElements.forEach(targetElement => {
                if (targetElement !== sourceElement) {
                    const targetScrollableHeight = targetElement.scrollHeight - targetElement.clientHeight;
                    if (targetScrollableHeight > 0) {
                        targetElement.scrollTop = targetScrollableHeight * scrollPercentage;
                    }
                }
            });
            requestAnimationFrame(() => { isSyncing = false; });
        });
    });
}

// BBR Modal Functions with Drag and Resize Support

// Add CSS for drag and resize functionality
function addBBRModalCSS() {
    if (document.getElementById('bbr-modal-css')) return;

    const css = document.createElement('style');
    css.id = 'bbr-modal-css';
    css.textContent = `
        .bbr-modal-draggable {
            position: absolute !important;
            top: 5rem !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            min-width: 400px !important;
            min-height: 300px !important;
            max-width: 90vw !important;
            max-height: 90vh !important;
        }

        .bbr-modal-header {
            cursor: move !important;
        }

        .resize-handle {
            position: absolute !important;
            background: transparent !important;
            z-index: 60 !important;
        }

        .resize-n { top: -2px; left: 10px; right: 10px; height: 5px; cursor: ns-resize; }
        .resize-s { bottom: -2px; left: 10px; right: 10px; height: 5px; cursor: ns-resize; }
        .resize-e { right: -2px; top: 10px; bottom: 10px; width: 5px; cursor: ew-resize; }
        .resize-w { left: -2px; top: 10px; bottom: 10px; width: 5px; cursor: ew-resize; }
        .resize-ne { top: -2px; right: -2px; width: 10px; height: 10px; cursor: nesw-resize; }
        .resize-nw { top: -2px; left: -2px; width: 10px; height: 10px; cursor: nwse-resize; }
        .resize-se { bottom: -2px; right: -2px; width: 10px; height: 10px; cursor: nwse-resize; }
        .resize-sw { bottom: -2px; left: -2px; width: 10px; height: 10px; cursor: nesw-resize; }
    `;
    document.head.appendChild(css);
}

// Show BBR modal with drag and resize support
function showBBRModal(bbr) {
    // Store current BBR data
    currentBBR = bbr;

    // Add CSS if not already added
    addBBRModalCSS();

    // Create modal HTML with resize handles
    const modalHtml = `
        <div id="bbr-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onclick="closeBBRModal(event)">
            <div id="bbr-modal-content" class="p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white bbr-modal-draggable" onmousedown="startDragging(event)" onclick="event.stopPropagation()">
                <!-- BBR Metadata -->
                <div class="mb-4 p-3 bg-gray-50 rounded-md">
                    <div class="grid grid-cols-2 gap-2 text-sm text-gray-600">
                        <div><strong>Created:</strong> ${new Date(bbr.created_at).toLocaleString()}</div>
                        <div><strong>Model:</strong> ${JSON.parse(bbr.model_info || '{}').model || 'N/A'}</div>
                        <div><strong>Tokens Used:</strong> ${bbr.tokens_used || 'N/A'}</div>
                        <div><strong>Cost:</strong> ¥${(bbr.cost || 0).toFixed(4)}</div>
                        <div><strong>Time Spent:</strong> ${bbr.time_spent ? (bbr.time_spent).toFixed(1) + 's' : 'N/A'}</div>
                    </div>
                </div>

                <!-- BBR Content -->
                <div class="mb-4">
                    <h4 class="text-sm font-medium text-gray-700 mb-2">Report Content</h4>
                    <div class="bg-gray-50 p-4 rounded border">
                        <pre class="text-xs text-gray-700 whitespace-pre-wrap break-words max-h-96 overflow-auto">${bbr.content}</pre>
                    </div>
                </div>

                <!-- Action Buttons -->
                <div class="mt-6 flex justify-end space-x-3">
                    <button onclick="copyBBRContent()" class="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">
                        Copy Content
                    </button>
                    <button onclick="closeBBRModal()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Close
                    </button>
                </div>

                <!-- Resize handles -->
                <div class="resize-handle resize-n" onmousedown="startResizing(event, 'n')"></div>
                <div class="resize-handle resize-s" onmousedown="startResizing(event, 's')"></div>
                <div class="resize-handle resize-e" onmousedown="startResizing(event, 'e')"></div>
                <div class="resize-handle resize-w" onmousedown="startResizing(event, 'w')"></div>
                <div class="resize-handle resize-ne" onmousedown="startResizing(event, 'ne')"></div>
                <div class="resize-handle resize-nw" onmousedown="startResizing(event, 'nw')"></div>
                <div class="resize-handle resize-se" onmousedown="startResizing(event, 'se')"></div>
                <div class="resize-handle resize-sw" onmousedown="startResizing(event, 'sw')"></div>
            </div>
        </div>
    `;

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Center the modal
    const modalContent = document.getElementById('bbr-modal-content');
    if (modalContent) {
        modalContent.style.left = '50%';
        modalContent.style.transform = 'translateX(-50%)';
    }
}

// Close BBR modal
function closeBBRModal(event) {
    // If event exists, check if it's a click on the background overlay
    if (event && event.target.id !== 'bbr-modal') {
        return;
    }

    const modal = document.getElementById('bbr-modal');
    if (modal) {
        modal.remove();
        isDragging = false;
        isResizing = false;
    }
}

// Copy BBR content
function copyBBRContent() {
    if (currentBBR) {
        navigator.clipboard.writeText(currentBBR.content).then(() => {
            showNotification('BBR content copied to clipboard', 'success');
        });
    }
}

// Drag functionality
function startDragging(event) {
    // Prevent dragging on buttons, resize handles, and the content area
    if (event.target.closest('button') || 
        event.target.closest('.resize-handle') ||
        event.target.closest('pre')) {
        return;
    }
    event.preventDefault();
    isDragging = true;
    const modal = document.getElementById('bbr-modal-content');
    if (!modal) return;
    const rect = modal.getBoundingClientRect();
    dragOffset.x = event.clientX - rect.left;
    dragOffset.y = event.clientY - rect.top;
    
    // Set position in pixels and remove transform to avoid jump
    modal.style.transform = 'none';
    modal.style.left = `${rect.left}px`;
    modal.style.top = `${rect.top}px`;
    modal.style.margin = '0';
    
    document.addEventListener('mousemove', handleDragging);
    document.addEventListener('mouseup', stopDragging);
}

function handleDragging(event) {
    if (!isDragging) return;
    const modal = document.getElementById('bbr-modal-content');
    if (!modal) return;
    let newX = event.clientX - dragOffset.x;
    let newY = event.clientY - dragOffset.y;
    
    // Constrain to viewport
    newX = Math.max(0, Math.min(newX, window.innerWidth - modal.offsetWidth));
    newY = Math.max(0, Math.min(newY, window.innerHeight - modal.offsetHeight));
    
    modal.style.left = `${newX}px`;
    modal.style.top = `${newY}px`;
}

function stopDragging() {
    isDragging = false;
    document.removeEventListener('mousemove', handleDragging);
    document.removeEventListener('mouseup', stopDragging);
}

// Resize functionality
function startResizing(event, handle) {
    event.preventDefault();
    event.stopPropagation();
    isResizing = true;
    currentResizeHandle = handle;
    const modal = document.getElementById('bbr-modal-content');
    if (!modal) return;

    const rect = modal.getBoundingClientRect();

    // Set position to pixels and remove transform
    modal.style.transform = 'none';
    modal.style.left = `${rect.left}px`;
    modal.style.top = `${rect.top}px`;
    modal.style.margin = '0';

    initialPos.x = rect.left;
    initialPos.y = rect.top;
    initialSize.width = rect.width;
    initialSize.height = rect.height;
    initialMousePos.x = event.clientX;
    initialMousePos.y = event.clientY;

    document.addEventListener('mousemove', handleResizing);
    document.addEventListener('mouseup', stopResizing);
}

function handleResizing(event) {
    if (!isResizing) return;
    const modal = document.getElementById('bbr-modal-content');
    if (!modal) return;

    const dx = event.clientX - initialMousePos.x;
    const dy = event.clientY - initialMousePos.y;

    let newWidth = initialSize.width;
    let newHeight = initialSize.height;
    let newLeft = initialPos.x;
    let newTop = initialPos.y;

    if (currentResizeHandle.includes('e')) {
        newWidth = initialSize.width + dx;
    }
    if (currentResizeHandle.includes('w')) {
        newWidth = initialSize.width - dx;
        newLeft = initialPos.x + dx;
    }
    if (currentResizeHandle.includes('s')) {
        newHeight = initialSize.height + dy;
    }
    if (currentResizeHandle.includes('n')) {
        newHeight = initialSize.height - dy;
        newTop = initialPos.y + dy;
    }

    const minWidth = 400;
    const minHeight = 300;

    if (newWidth >= minWidth) {
        modal.style.width = `${newWidth}px`;
        modal.style.left = `${newLeft}px`;
    }
    if (newHeight >= minHeight) {
        modal.style.height = `${newHeight}px`;
        modal.style.top = `${newTop}px`;
    }
}

function stopResizing() {
    isResizing = false;
    currentResizeHandle = null;
    document.removeEventListener('mousemove', handleResizing);
    document.removeEventListener('mouseup', stopResizing);
}

// Initialize common functions when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize sync scroll if needed
    initializeSyncScroll();
});

// Export functions to global scope for inline event handlers
window.VPSWeb = {
    showToast,
    showError,
    showSuccessMessage,
    showNotification,
    escapeHtml,
    initializeSyncScroll,
    showBBRModal,
    closeBBRModal,
    copyBBRContent,
    startDragging,
    handleDragging,
    stopDragging,
    startResizing,
    handleResizing,
    stopResizing
};

// Also export drag/resize functions directly to global scope for inline handlers
window.startDragging = startDragging;
window.handleDragging = handleDragging;
window.stopDragging = stopDragging;
window.startResizing = startResizing;
window.handleResizing = handleResizing;
window.stopResizing = stopResizing;