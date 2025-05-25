import { db } from './firebase.js';
import { collection, addDoc, getDocs, doc, updateDoc, deleteDoc, query, where } from "firebase/firestore";

// Collection reference
const ramensCollection = collection(db, 'ramens');

// Add a new ramen
export const addRamen = async (ramenData) => {
  try {
    const docRef = await addDoc(ramensCollection, {
      name: ramenData.name,
      restaurant: ramenData.restaurant,
      address: ramenData.address,
      price: ramenData.price,
      rating: ramenData.rating,
      type: ramenData.type, // e.g., 'Shoyu', 'Miso', 'Tonkotsu'
      description: ramenData.description,
      imageUrl: ramenData.imageUrl,
      createdAt: new Date(),
      updatedAt: new Date()
    });
    return docRef.id;
  } catch (error) {
    console.error("Error adding ramen: ", error);
    throw error;
  }
};

// Get all ramens
export const getAllRamens = async () => {
  try {
    const querySnapshot = await getDocs(ramensCollection);
    return querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  } catch (error) {
    console.error("Error getting ramens: ", error);
    throw error;
  }
};

// Update a ramen
export const updateRamen = async (id, updateData) => {
  try {
    const ramenRef = doc(db, 'ramens', id);
    await updateDoc(ramenRef, {
      ...updateData,
      updatedAt: new Date()
    });
  } catch (error) {
    console.error("Error updating ramen: ", error);
    throw error;
  }
};

// Delete a ramen
export const deleteRamen = async (id) => {
  try {
    const ramenRef = doc(db, 'ramens', id);
    await deleteDoc(ramenRef);
  } catch (error) {
    console.error("Error deleting ramen: ", error);
    throw error;
  }
};

// Search ramens by type
export const searchRamensByType = async (type) => {
  try {
    const q = query(ramensCollection, where("type", "==", type));
    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  } catch (error) {
    console.error("Error searching ramens: ", error);
    throw error;
  }
}; 