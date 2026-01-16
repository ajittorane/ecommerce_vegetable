document.addEventListener("DOMContentLoaded", () => {

  /* ===========================
     CART PAGE: INCREASE / DECREASE
  =========================== */
  const cartTable = document.getElementById("cart-table");
  const grandTotalEl = document.getElementById("grand-total");

  if (cartTable) {

    const updateCartTotals = () => {
      let grandTotal = 0;

      document.querySelectorAll("#cart-table tbody tr").forEach(row => {
        const price = parseFloat(row.dataset.price) || 0;
        const qtyInput = row.querySelector(".quantity-input");
        const totalEl = row.querySelector(".product-total");

        let qty = parseInt(qtyInput.value) || 1;
        if (qty < 1) qty = 1;

        const total = price * qty;
        totalEl.textContent = "₹" + total.toFixed(2);
        grandTotal += total;
      });

      if (grandTotalEl) {
        grandTotalEl.textContent = "₹" + grandTotal.toFixed(2);
      }
    };

    document.querySelectorAll(".quantity-control").forEach(control => {
      const row = control.closest("tr");
      const orderId = row.dataset.orderId;
      const minus = control.querySelector(".btn-minus");
      const plus = control.querySelector(".btn-plus");

      const updateServer = (action) => {
        fetch(`/update_cart/${orderId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest"
          },
          body: `action=${action}`
        })
        .then(() => updateCartTotals());
      };

      minus?.addEventListener("click", () => updateServer("decrease"));
      plus?.addEventListener("click", () => updateServer("increase"));
    });

    updateCartTotals();
  }

  /* ===========================
     ADD TO CART (HOME / PRODUCTS)
     Quantity = 1 ONLY
  =========================== */
  document.querySelectorAll(".add-to-cart-btn").forEach(button => {

    button.addEventListener("click", (e) => {
      e.preventDefault();

      if (button.disabled) return;

      const form = button.closest("form");
      if (!form) return;

      const originalText = button.innerHTML;
      button.disabled = true;
      button.innerHTML = "Adding...";

      fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        }
      })
      .then(() => {

        /* === Toast Message === */
        const toast = document.createElement("div");
        toast.className = "alert alert-success position-fixed top-0 end-0 m-4";
        toast.style.zIndex = "9999";
        toast.textContent = "🛒 Added to cart successfully";
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 1500);

        /* === Navbar Cart Count === */
        const cartCount = document.getElementById("cart-count");
        if (cartCount) {
          cartCount.textContent =
            (parseInt(cartCount.textContent) || 0) + 1;
        }

        /* === Button Feedback === */
        button.innerHTML = "✓ Added";
        setTimeout(() => {
          button.innerHTML = originalText;
          button.disabled = false;
        }, 1200);
      })
      .catch(err => {
        console.error(err);
        alert("Failed to add product!");
        button.innerHTML = originalText;
        button.disabled = false;
      });
    });

  });

});
