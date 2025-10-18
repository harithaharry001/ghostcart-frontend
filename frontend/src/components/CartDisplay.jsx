/**
 * Cart Display Component
 * Shows cart contents with total breakdown
 */
import React from 'react';

export default function CartDisplay({ cart, onApprove }) {
  if (!cart) return null;

  const { items, total } = cart;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-xl font-bold mb-4">Your Cart</h3>

      {/* Line Items */}
      <div className="space-y-3 mb-4">
        {items.map((item, idx) => (
          <div key={idx} className="flex justify-between items-center py-2 border-b border-gray-100">
            <div>
              <div className="font-medium">{item.product_name}</div>
              <div className="text-sm text-gray-500">Qty: {item.quantity} × ${(item.unit_price_cents / 100).toFixed(2)}</div>
            </div>
            <div className="font-bold">${(item.subtotal_cents / 100).toFixed(2)}</div>
          </div>
        ))}
      </div>

      {/* Totals */}
      <div className="space-y-2 border-t border-gray-200 pt-4">
        <div className="flex justify-between text-sm">
          <span>Subtotal:</span>
          <span>${(total.subtotal_cents / 100).toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span>Tax:</span>
          <span>${(total.tax_cents / 100).toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span>Shipping:</span>
          <span>${(total.shipping_cents / 100).toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-xl font-bold border-t border-gray-300 pt-2">
          <span>Total:</span>
          <span className="text-primary">${(total.total_cents / 100).toFixed(2)}</span>
        </div>
      </div>

      <button
        onClick={onApprove}
        className="w-full mt-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-bold text-lg"
      >
        Approve Purchase
      </button>
    </div>
  );
}
