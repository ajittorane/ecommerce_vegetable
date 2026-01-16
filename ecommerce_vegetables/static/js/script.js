document.addEventListener("DOMContentLoaded", () => {

  /* ===========================
     QUANTITY CONTROLS (Product / Home / Cart)
  =========================== */
  document.querySelectorAll(".quantity-control").forEach(container => {
    const qtyInput = container.querySelector(".quantity-input");
    const form = container.closest("form");
    const hiddenQty = form?.querySelector(".cart-quantity");
    const btnMinus = container.querySelector(".btn-minus");
    const btnPlus = container.querySelector(".btn-plus");

    if (!qtyInput) return;

    const updateHidden = () => {
      if (hiddenQty) hiddenQty.value = qtyInput.value;
    };

    btnMinus?.addEventListener("click", () => {
      let val = parseInt(qtyInput.value) || 1;
      if (val > 1) val--;
      qtyInput.value = val;
      updateHidden();
    });

    btnPlus?.addEventListener("click", () => {
      let val = parseInt(qtyInput.value) || 1;
      qtyInput.value = val + 1;
      updateHidden();
    });

    qtyInput.addEventListener("input", () => {
      let val = parseInt(qtyInput.value) || 1;
      if (val < 1) val = 1;
      qtyInput.value = val;
      updateHidden();
    });
  });

  /* ===========================
     CART PAGE TOTAL CALCULATION
  =========================== */
  const cartTable = document.getElementById("cart-table");
  const grandTotalEl = document.getElementById("grand-total");

  if (cartTable) {
    const cartRows = cartTable.querySelectorAll("tbody tr");

    const updateCartTotals = () => {
      let grandTotal = 0;
      cartRows.forEach(row => {
        const price = parseFloat(row.dataset.price) || 0;
        const qtyInput = row.querySelector(".quantity-input");
        const totalEl = row.querySelector(".product-total");
        let qty = parseInt(qtyInput.value) || 1;
        if (qty < 1) qty = 1;
        const total = price * qty;
        if (totalEl) totalEl.textContent = "₹" + total.toFixed(2);
        grandTotal += total;
      });
      if (grandTotalEl) grandTotalEl.textContent = "₹" + grandTotal.toFixed(2);
    };

    cartRows.forEach(row => {
      const minus = row.querySelector(".btn-minus");
      const plus = row.querySelector(".btn-plus");
      const qtyInput = row.querySelector(".quantity-input");
      const orderId = row.dataset.orderId;

      const updateServer = (action) => {
        fetch(`/update_cart/${orderId}`, {
          method: "POST",
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: `action=${action}`
        }).then(() => updateCartTotals());
      };

      minus?.addEventListener("click", () => updateServer("decrease"));
      plus?.addEventListener("click", () => updateServer("increase"));
      qtyInput?.addEventListener("input", updateCartTotals);
    });

    // Initial calculation
    updateCartTotals();
  }

  /* ===========================
     ADD TO CART BUTTON FEEDBACK
  =========================== */
  document.querySelectorAll(".add-to-cart").forEach(btn => {
    btn.addEventListener("click", (e) => {
      // Prevent double submission
      btn.disabled = true;

      const originalText = btn.innerHTML;
      btn.innerHTML = "✓ Added";

      // Re-enable button after short delay
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      }, 1000);
    });
  });

});
